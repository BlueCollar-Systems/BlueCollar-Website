from pathlib import Path
import copy
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("release_snapshot", Path(__file__).resolve().parents[1] / "tools/release_snapshot.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class FakeGitHub:
    def __init__(self, proof, files, existing=False):
        self.proof = proof; self.files = files; self.calls = []; self.tag = proof["source_commit"] if existing else None
        self.release = self.make_release(False) if existing else None
        self.corrupt_download = False; self.after_draft_tag = None; self.stale_list = False; self.list_calls = 0
    def make_release(self, draft):
        return {"id": 101, "tag_name": self.proof["tag"], "target_commitish": self.proof["source_commit"], "draft": draft, "prerelease": False,
                "assets": [{"id": index, "name": p.name, "state": "uploaded", "size": p.stat().st_size, "digest": "sha256:" + m.digest(p)} for index, p in enumerate(self.files, 1)]}
    def api(self, suffix, method="GET", body=None, **_kwargs):
        self.calls.append((method,suffix,body))
        if suffix.startswith("commits/"): return {"sha":self.proof["source_commit"]}
        if method == "PATCH": self.release["draft"] = False; self.tag = self.proof["source_commit"]
        return copy.deepcopy(self.release)
    def tag_commit(self, _tag): return self.tag
    def find_release(self, _tag):
        self.list_calls += 1
        return None if self.stale_list else copy.deepcopy(self.release)
    def create_draft(self, proof, files):
        self.calls.append(("create",proof["source_commit"],None))
        self.release = self.make_release(True)
        if self.after_draft_tag: self.tag = self.after_draft_tag
        return self.release["id"]
    def read_release(self, release_id): return self.api("releases/" + str(release_id))
    def download(self, asset_id, destination):
        destination.write_bytes(b"wrong downloaded bytes" if self.corrupt_download else self.files[asset_id-1].read_bytes())


class ReleaseSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name) / "repo"; self.root.mkdir()
        def g(*args): subprocess.run(["git","-C",str(self.root),*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.g = g
        g("init");g("config","user.name","Fictional Test");g("config","user.email","fixture@example.invalid")
        (self.root / "VERSION").write_text("1.0.106\n");(self.root / "index.html").write_text("original source\n")
        g("add",".");g("commit","-m","fixture initial source")
        self.patch = patch.object(m,"ROOT",self.root);self.patch.start()
        self.sidecar = m.prepare("1.0.106","Fictional/Website",Path(self.temp.name)/"release")
        self.proof = json.loads(self.sidecar.read_text());self.files = [self.sidecar.with_name(self.proof["archive"]["name"]),self.sidecar]
    def tearDown(self): self.patch.stop();self.temp.cleanup()
    def fake(self,existing=False):return FakeGitHub(self.proof,self.files,existing)
    def test_main_advance_keeps_archive_and_release_on_original_source(self):
        original=self.proof["source_commit"]
        (self.root/"index.html").write_text("concurrent new main\n");self.g("add",".");self.g("commit","-m","main advanced")
        self.assertNotEqual(m.git("rev-parse","HEAD"),original)
        client=self.fake();result=m.publish(self.sidecar,client)
        self.assertEqual(result["source_commit"],original)
        self.assertIn(("create",original,None),client.calls)
        self.assertFalse(client.release["draft"])
    def test_structured_create_returns_validated_id_and_uploads_both_assets(self):
        with patch.dict(m.os.environ,{"GH_TOKEN":"fictional-token"}):
            client=m.GitHub("Fictional/Website")
            response=self.fake().make_release(True);response["assets"]=[]
            response["upload_url"]="https://evil.invalid/ignored"
            with patch.object(client,"api",return_value=response) as api,patch.object(client,"upload") as upload:
                self.assertEqual(client.create_draft(self.proof,self.files),101)
                api.assert_called_once()
                self.assertEqual(api.call_args.args,("releases",))
                self.assertEqual(api.call_args.kwargs["method"],"POST")
                body=api.call_args.kwargs["body"]
                self.assertEqual(body["target_commitish"],self.proof["source_commit"])
                self.assertEqual(body["tag_name"],self.proof["tag"])
                self.assertIs(body["draft"],True);self.assertIs(body["prerelease"],False)
                self.assertEqual([call.args for call in upload.call_args_list],[(101,self.files[0]),(101,self.files[1])])
    def test_created_wrong_id_source_or_state_is_rejected_before_upload(self):
        for fields in [{"id":True},{"id":0},{"tag_name":"v1.0.999"},{"target_commitish":"main"},{"draft":False},{"prerelease":True}]:
            with self.subTest(fields=fields),patch.dict(m.os.environ,{"GH_TOKEN":"fictional-token"}):
                client=m.GitHub("Fictional/Website");response=self.fake().make_release(True);response["assets"]=[];response.update(fields)
                with patch.object(client,"api",return_value=response),patch.object(client,"upload") as upload:
                    with self.assertRaises(ValueError):client.create_draft(self.proof,self.files)
                    upload.assert_not_called()
    def test_stale_release_list_cannot_hide_returned_numeric_draft(self):
        client=self.fake();client.stale_list=True
        result=m.publish(self.sidecar,client)
        self.assertEqual(result["release_id"],101);self.assertEqual(client.list_calls,1)
        self.assertEqual([call[1] for call in client.calls if call[0]=="GET" and call[1].startswith("releases/")],["releases/101","releases/101"])
    def test_upload_uses_fixed_host_numeric_id_and_encoded_name(self):
        asset=Path(self.temp.name)/"asset + ü#.json";asset.write_bytes(b"{}")
        response={"id":77,"name":asset.name,"state":"uploaded","size":2,"digest":"sha256:"+m.digest(asset)}
        with patch.dict(m.os.environ,{"GH_TOKEN":"fictional-token"}):
            client=m.GitHub("Fictional/Website")
            with patch.object(client.opener,"open",return_value=io.BytesIO(json.dumps(response).encode())) as opened:
                client.upload(101,asset)
                request=opened.call_args.args[0]
                self.assertEqual(request.full_url,"https://uploads.github.com/repos/Fictional/Website/releases/101/assets?name=asset%20%2B%20%C3%BC%23.json")
                self.assertEqual(request.method,"POST");self.assertEqual(request.data,b"{}")
                self.assertEqual(request.get_header("Content-type"),"application/json")
    def test_upload_digest_mismatch_and_redirect_are_rejected(self):
        with patch.dict(m.os.environ,{"GH_TOKEN":"fictional-token"}):
            client=m.GitHub("Fictional/Website")
            response={"id":77,"name":self.files[0].name,"state":"uploaded","size":self.files[0].stat().st_size,"digest":"sha256:"+"0"*64}
            with patch.object(client.opener,"open",return_value=io.BytesIO(json.dumps(response).encode())):
                with self.assertRaisesRegex(ValueError,"response differs"):client.upload(101,self.files[0])
        with self.assertRaisesRegex(ValueError,"redirect"):m.NoRedirect().redirect_request(None,None,None,None,None,None)
    def test_direct_release_read_bypasses_cache_and_checks_returned_id(self):
        with patch.dict(m.os.environ,{"GH_TOKEN":"fictional-token"}):
            client=m.GitHub("Fictional/Website")
            with patch.object(client,"api",return_value={"id":101}) as api:
                self.assertEqual(client.read_release(101),{"id":101})
                self.assertRegex(api.call_args.args[0],r"^releases/101\?bcs_snapshot_read=\d+$")
            with patch.object(client,"api",return_value={"id":102}):
                with self.assertRaisesRegex(ValueError,"id mismatch"):client.read_release(101)
    def test_mismatched_existing_tag_never_mints_or_publishes(self):
        client=self.fake();client.tag="f"*40
        with self.assertRaisesRegex(ValueError,"Existing tag"):m.publish(self.sidecar,client)
        self.assertFalse(any(x[0] in ("create","PATCH") for x in client.calls))
    def test_existing_source_mismatch_and_incomplete_assets_fail(self):
        for change in [lambda r:r.update(target_commitish="main"),lambda r:r["assets"].pop(),lambda r:r["assets"][0].update(digest=None),lambda r:r["assets"][0].update(size=0)]:
            with self.subTest(change=change):
                client=self.fake(True);change(client.release)
                with self.assertRaises(ValueError):m.publish(self.sidecar,client)
                self.assertFalse(any(x[0] in ("create","PATCH") for x in client.calls))
    def test_complete_existing_release_is_verified_without_mutation(self):
        client=self.fake(True);self.assertEqual(m.publish(self.sidecar,client)["status"],"VERIFIED_EXISTING_RELEASE")
        self.assertFalse(any(x[0] in ("create","PATCH") for x in client.calls))
    def test_existing_draft_requires_inspection(self):
        client=self.fake(True);client.release["draft"]=True
        with self.assertRaisesRegex(ValueError,"Existing draft"):m.publish(self.sidecar,client)
        self.assertFalse(any(x[0]=="PATCH" for x in client.calls))
    def test_downloaded_byte_mismatch_keeps_new_draft_unpublished(self):
        client=self.fake();client.corrupt_download=True
        with self.assertRaisesRegex(ValueError,"Downloaded bytes"):m.publish(self.sidecar,client)
        self.assertTrue(client.release["draft"]);self.assertFalse(any(x[0]=="PATCH" for x in client.calls))
    def test_tag_changes_during_mint_do_not_publish(self):
        client=self.fake();client.after_draft_tag="f"*40
        with self.assertRaisesRegex(ValueError,"Tag source mismatch"):m.publish(self.sidecar,client)
        self.assertFalse(any(x[0]=="PATCH" for x in client.calls))
    def test_local_archive_drift_or_forged_sidecar_rejected_before_network(self):
        self.files[0].write_bytes(b"altered archive")
        client=self.fake()
        with self.assertRaisesRegex(ValueError,"Local archive drift"):m.publish(self.sidecar,client)
        self.assertEqual(client.calls,[])
        proof=copy.deepcopy(self.proof);proof["archive"]["bytes"]=self.files[0].stat().st_size;proof["archive"]["sha256"]=m.digest(self.files[0]);self.sidecar.write_text(json.dumps(proof))
        with self.assertRaisesRegex(ValueError,"exact pinned Git source"):m.publish(self.sidecar,client)
        self.assertEqual(client.calls,[])
    def test_prepare_does_not_overwrite_or_accept_wrong_version(self):
        with self.assertRaisesRegex(ValueError,"already exists"):m.prepare("1.0.106","Fictional/Website",self.sidecar.parent)
        with self.assertRaisesRegex(ValueError,"VERSION differs"):m.prepare("1.0.107","Fictional/Website",Path(self.temp.name)/"wrong")


if __name__=="__main__":unittest.main()

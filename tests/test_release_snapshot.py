from pathlib import Path
import copy
import importlib.util
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
        self.corrupt_download = False; self.after_draft_tag = None
    def make_release(self, draft):
        return {"id": 101, "tag_name": self.proof["tag"], "target_commitish": self.proof["source_commit"], "draft": draft, "prerelease": False,
                "assets": [{"id": index, "name": p.name, "state": "uploaded", "size": p.stat().st_size, "digest": "sha256:" + m.digest(p)} for index, p in enumerate(self.files, 1)]}
    def api(self, suffix, method="GET", body=None, **_kwargs):
        self.calls.append((method,suffix,body))
        if suffix.startswith("commits/"): return {"sha":self.proof["source_commit"]}
        if method == "PATCH": self.release["draft"] = False; self.tag = self.proof["source_commit"]
        return copy.deepcopy(self.release)
    def tag_commit(self, _tag): return self.tag
    def find_release(self, _tag): return copy.deepcopy(self.release)
    def create_draft(self, proof, files):
        self.calls.append(("create",proof["source_commit"],None))
        self.release = self.make_release(True)
        if self.after_draft_tag: self.tag = self.after_draft_tag
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
    def test_create_cli_uses_full_target_and_draft_before_publish(self):
        with patch.dict(m.os.environ,{"GH_TOKEN":"fictional-token"}),patch.object(m.subprocess,"run") as run:
            run.return_value.returncode=0
            m.GitHub("Fictional/Website").create_draft(self.proof,self.files)
            command=run.call_args.args[0]
            self.assertEqual(command[command.index("--target")+1],self.proof["source_commit"])
            self.assertIn("--draft",command);self.assertNotIn("--clobber",command)
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

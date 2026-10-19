from pathlib import Path
import ast, json, os, re, shutil, subprocess, sys, tempfile, textwrap, unittest
ROOT=Path(__file__).resolve().parents[1]
def block(text,name,kind='job'):
    if kind=='job': pattern=r'(?ms)^  '+re.escape(name)+r':\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)'
    else: pattern=r'(?ms)^      - name: '+re.escape(name)+r'\n(.*?)(?=^      - (?:name:|uses:)|\Z)'
    match=re.search(pattern,text)
    if not match: raise AssertionError('Missing block '+name)
    return match.group(1)
def guard(body):
    match=re.search(r'^\s+if: (.+)$',body,re.M)
    if not match: raise AssertionError('Missing publication guard')
    value=match.group(1).strip()
    return ast.literal_eval(value) if value.startswith('"') else value
def run_guard(expression,event,flag,key,ref='refs/heads/main',action=''):
    return bool(run_expression(expression,event,flag,key,ref,action))
def run_expression(expression,event,flag,key,ref='refs/heads/main',action=''):
    values={'github.event_name':event,'github.ref':ref,'inputs.'+key:flag,'github.event.action':action,
      'github.event.head_commit.message':'normal source change',
      'needs.source-only-build-windows.outputs.publication_ready':'true',
      'steps.preflight.outputs.release':'true','steps.mint.outputs.release_verified':'true'}
    expression=re.sub(r'\b(?:github|inputs|needs|steps)(?:\.[A-Za-z0-9_-]+)+',lambda m:repr(values.get(m.group(0),'')),expression)
    expression=expression.replace('&&',' and ').replace('||',' or ')
    expression=re.sub(r'!(?!=)',' not ',expression)
    expression=re.sub(r'\btrue\b','True',expression)
    expression=re.sub(r'\bfalse\b','False',expression).strip()
    tree=ast.parse(expression,mode='eval')
    allowed=(ast.Expression,ast.BoolOp,ast.And,ast.Or,ast.UnaryOp,ast.Not,ast.Compare,ast.Eq,ast.NotEq,ast.Constant,ast.Call,ast.Name,ast.Load)
    for node in ast.walk(tree):
        if not isinstance(node,allowed):raise AssertionError('Unsupported condition')
        if isinstance(node,ast.Name) and node.id not in ('startsWith','contains'):raise AssertionError('Unknown function')
        if isinstance(node,ast.Call) and not isinstance(node.func,ast.Name):raise AssertionError('Unsafe call')
    return eval(compile(tree,'<guard>','eval'),{'__builtins__':{},'startsWith':lambda v,p:str(v).startswith(p),'contains':lambda v,p:p in str(v)})
def concurrency(text):
    header=text.split('\njobs:',1)[0]
    match=re.search(r'(?m)^concurrency:\n  group: (.+)\n  cancel-in-progress: (.+)$',header)
    if not match: raise AssertionError('Missing concurrency block')
    return match.groups()
def expression_inside(value):
    match=re.fullmatch(r'\$\{\{ (.+) \}\}',value.strip())
    if not match: raise AssertionError('Not a single expression: '+value)
    return match.group(1)
DISPATCH_TYPES=['product-release','product-update','steel-shapes-release','steel-shapes-update','']
class ManualPublicationWorkflowTest(unittest.TestCase):
    def manual_gate(self,expression,key):
        for event in ['push','pull_request','schedule','repository_dispatch','release']:
            for flag in [False,True,None,'false']:
                with self.subTest(event=event,flag=flag):self.assertFalse(run_guard(expression,event,flag,key))
        for flag in [False,None,'false']:
            self.assertFalse(run_guard(expression,'workflow_dispatch',flag,key))
        self.assertTrue(run_guard(expression,'workflow_dispatch',True,key))
    def boolean_false(self,text,key):
        header=text.split('\njobs:',1)[0]
        match=re.search(r'(?ms)^      '+re.escape(key)+r':\n(.*?)(?=^      [A-Za-z0-9_-]+:|\n\S|\Z)',header)
        self.assertIsNotNone(match)
        self.assertRegex(match.group(1),r'(?m)^        type: boolean$')
        self.assertRegex(match.group(1),r'(?m)^        default: false$')
    def test_release_and_version_bump_need_manual_true(self):
        text=(ROOT/'.github/workflows/auto-release.yml').read_text(encoding='utf-8')
        self.boolean_false(text,'publish_release')
        self.manual_gate(guard(block(text,'release')),'publish_release')
        expression=guard(block(text,'build-only'))
        self.assertTrue(run_guard(expression,'workflow_dispatch',False,'publish_release'))
        self.assertFalse(run_guard(expression,'workflow_dispatch',True,'publish_release'))
        self.assertFalse(run_guard(expression,'push',False,'publish_release'))
        readonly=block(text,'build-only')
        for forbidden in ['git push','gh release','write_text','sync_repo_metadata']:
            self.assertNotIn(forbidden,readonly)
    def test_production_requires_manual_main_or_product_release(self):
        text=(ROOT/'.github/workflows/website-ci.yml').read_text(encoding='utf-8')
        self.boolean_false(text,'deploy_production')
        expression=guard(block(text,'deploy-pages'))
        key='deploy_production'
        # Ordinary pushes, pull requests, the schedule and other events never
        # deploy, whatever the flag or a dispatch type would say.
        for event in ['push','pull_request','schedule','release']:
            for flag in [False,True,None,'false']:
                for action in DISPATCH_TYPES:
                    with self.subTest(event=event,flag=flag,action=action):
                        self.assertFalse(run_guard(expression,event,flag,key,action=action))
        # Manual runs deploy only with deploy_production=true, only from main.
        for flag in [False,None,'false']:
            self.assertFalse(run_guard(expression,'workflow_dispatch',flag,key))
        self.assertTrue(run_guard(expression,'workflow_dispatch',True,key))
        self.assertFalse(run_guard(expression,'workflow_dispatch',True,key,'refs/heads/unreviewed'))
        # O13: an importer's product-release dispatch deploys (deploy only);
        # every other dispatch type stays validation-only.
        for action in DISPATCH_TYPES:
            for flag in [None,True]:
                with self.subTest(action=action,flag=flag):
                    self.assertEqual(run_guard(expression,'repository_dispatch',flag,key,action=action),action=='product-release')
        self.assertFalse(run_guard(expression,'repository_dispatch',None,key,'refs/heads/unreviewed','product-release'))
        self.assertNotIn('inputs.deploy_production',block(text,'static-checks'))
        self.assertIn("'production' || 'validation'",text)
        for event in ['push:','pull_request:','schedule:','repository_dispatch:']:self.assertIn(event,text)
    def test_release_deploys_share_the_production_group_and_queue(self):
        text=(ROOT/'.github/workflows/website-ci.yml').read_text(encoding='utf-8')
        group,cancel=concurrency(text)
        self.assertTrue(group.startswith('website-ci-${{ github.ref }}-'))
        group_expression=expression_inside(group.split('${{ github.ref }}-',1)[1])
        cancel_expression=expression_inside(cancel)
        key='deploy_production'
        def lane(event,flag=None,action=''):
            return run_expression(group_expression,event,flag,key,action=action)
        self.assertEqual(lane('workflow_dispatch',True),'production')
        self.assertEqual(lane('repository_dispatch',action='product-release'),'production')
        for event,flag,action in [('workflow_dispatch',False,''),('push',True,''),('schedule',None,''),
                                  ('pull_request',None,''),('repository_dispatch',None,'product-update'),
                                  ('repository_dispatch',None,'steel-shapes-release')]:
            with self.subTest(event=event,action=action):self.assertEqual(lane(event,flag,action),'validation')
        # A release deploy waits for a running deploy; manual and validation
        # runs keep the old cancel-in-progress behaviour.
        self.assertFalse(run_guard(cancel_expression,'repository_dispatch',None,key,action='product-release'))
        for event,flag,action in [('workflow_dispatch',True,''),('workflow_dispatch',False,''),('push',None,''),
                                  ('schedule',None,''),('repository_dispatch',None,'product-update')]:
            with self.subTest(event=event,action=action):self.assertTrue(run_guard(cancel_expression,event,flag,key,action=action))
    def test_release_deploy_is_metadata_only_and_reuses_the_deploy_steps(self):
        text=(ROOT/'.github/workflows/website-ci.yml').read_text(encoding='utf-8')
        deploy=block(text,'deploy-pages')
        step=block(deploy,'Confirm a release deploy changes only download metadata','step')
        self.assertEqual(guard(step),"github.event_name == 'repository_dispatch'")
        self.assertIn('python tools/check_metadata_only_deploy.py --site _site --metadata repo-metadata.json',step)
        self.assertNotIn('secrets.',step)
        order=['Build repository metadata snapshot','Validate final immutable release metadata','Build site folder',
               'Confirm a release deploy changes only download metadata','Deploy to Cloudflare Pages',
               'Verify public download metadata','Check live links the way a visitor sees them',
               'Commit stamped version badges back to repo']
        positions=[deploy.index('      - name: '+name+'\n') for name in order]
        self.assertEqual(positions,sorted(positions))
        # One deploy job, one Cloudflare upload: the release path adds no
        # second copy of the secrets handling.
        self.assertEqual(text.count('wrangler@'),1)
        self.assertEqual(text.count('secrets.CLOUDFLARE_ACCOUNT_ID'),1)
        self.assertRegex(deploy,r'(?m)^      actions: read$')
        # No snapshot release from a dispatch: the website auto-release does
        # not listen to repository_dispatch.
        release=(ROOT/'.github/workflows/auto-release.yml').read_text(encoding='utf-8').split('\njobs:',1)[0]
        self.assertNotIn('repository_dispatch',release)
    def test_release_drift_workflow_only_reads_the_site(self):
        text=(ROOT/'.github/workflows/release-drift.yml').read_text(encoding='utf-8')
        header=text.split('\njobs:',1)[0]
        self.assertRegex(header,r'(?m)^  schedule:\n    - cron: "\d+ \d+ \* \* \*"$')
        self.assertRegex(header,r'(?m)^permissions:\n  contents: read\n  issues: write\n\n')
        self.assertIn('python tools/check_release_drift.py --report',text)
        for forbidden in ['wrangler','CLOUDFLARE','deploy_production: true','git push','python tools/sync_repo_metadata.py','python tools/build_site.py']:
            self.assertNotIn(forbidden,text)
        for name in ['Open or update the drift issue','Close the drift issue when no download is stale']:
            self.assertIn("github.event_name != 'pull_request'",guard(block(text,name,'step')))
        self.assertEqual(guard(block(text,'Fail when a download is stale or the check could not run','step')),
                         "steps.drift.outputs.status != '0'")
    def test_release_drift_crash_never_opens_the_issue(self):
        # Only status 1 opens the issue, and status 1 needs the tool's stale
        # marker in a finished report: a Python crash (exit 1) or any other
        # code is status 2, red but with no drift claim.
        text=(ROOT/'.github/workflows/release-drift.yml').read_text(encoding='utf-8')
        self.assertEqual(guard(block(text,'Open or update the drift issue','step')),
                         "steps.drift.outputs.status == '1' && github.event_name != 'pull_request'")
        self.assertEqual(guard(block(text,'Close the drift issue when no download is stale','step')),
                         "steps.drift.outputs.status == '0' && github.event_name != 'pull_request'")
        tool=(ROOT/'tools/check_release_drift.py').read_text(encoding='utf-8')
        marker=re.search(r'(?m)^STALE_MARKER = "([^"]+)"$',tool).group(1)
        step=block(text,'Compare live download metadata with GitHub releases','step')
        self.assertIn("grep -qF '"+marker+"'",step)
        call='python tools/check_release_drift.py --report "$RUNNER_TEMP/release-drift.md"'
        self.assertIn(call,step)
        bash=shutil.which('bash')
        if not bash: self.skipTest('bash is not available')
        script=textwrap.dedent(step.split('run: |\n',1)[1])
        cases=[(0,'in sync','0'),(1,marker+'\nstale','1'),(1,'no marker','2'),(1,None,'2'),
               (2,'could not run','2'),(120,None,'2')]
        for code,report,expected in cases:
            with self.subTest(code=code,report=report), tempfile.TemporaryDirectory() as temp:
                folder=Path(temp)
                if report is not None:(folder/'release-drift.md').write_text(report+'\n',encoding='utf-8')
                (folder/'step.sh').write_text(script.replace(call,'(exit %d)'%code),encoding='utf-8',newline='\n')
                env=dict(os.environ,RUNNER_TEMP=folder.as_posix(),GITHUB_OUTPUT=(folder/'out').as_posix(),
                         GITHUB_STEP_SUMMARY=(folder/'summary').as_posix())
                # GitHub's default bash for run steps.
                result=subprocess.run([bash,'--noprofile','--norc','-eo','pipefail',(folder/'step.sh').as_posix()],
                                      env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual((folder/'out').read_text(encoding='utf-8').strip(),'status='+expected)
    def upload_script(self):
        """The Cloudflare step's shell after the Python credential precheck."""
        text=(ROOT/'.github/workflows/website-ci.yml').read_text(encoding='utf-8')
        step=block(block(text,'deploy-pages'),'Deploy to Cloudflare Pages','step')
        body=[]
        for line in step.split('run: |\n',1)[1].split('\n'):
            if line.strip() and not line.startswith(' '*10):break
            body.append(line)
        precheck,upload=textwrap.dedent('\n'.join(body)).split('\nPY\n',1)
        self.assertIn("python - <<'PY'",precheck)
        return upload
    def run_upload(self,folder,checkout,runner_temp):
        """Run the upload commands in a fake checkout with a recording npx."""
        bash=shutil.which('bash')
        if not bash: self.skipTest('bash is not available')
        script=folder/'upload.sh'
        script.write_text(self.upload_script(),encoding='utf-8',newline='\n')
        binary=folder/'bin'; binary.mkdir(exist_ok=True)
        recorder=folder/'record_npx.py'
        recorder.write_text(
            'import json, os, sys\n'
            'from pathlib import Path\n'
            'here = Path.cwd()\n'
            'Path(os.environ["NPX_RECORD"]).write_text(json.dumps(\n'
            '    {"cwd": str(here), "args": sys.argv[1:], "listing": sorted(os.listdir(here))}), encoding="utf-8")\n',
            encoding='utf-8',newline='\n')
        npx=binary/'npx'
        npx.write_text('#!/usr/bin/env bash\nexec "$NPX_PYTHON" "$NPX_RECORDER" "$@"\n',encoding='utf-8',newline='\n')
        npx.chmod(0o755)
        record=folder/'npx.json'
        if record.exists():record.unlink()
        env=dict(os.environ,PATH=str(binary)+os.pathsep+os.environ.get('PATH',''),RUNNER_TEMP=runner_temp.as_posix(),
                 NPX_PYTHON=Path(sys.executable).as_posix(),NPX_RECORDER=recorder.as_posix(),NPX_RECORD=record.as_posix(),
                 GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='safe.directory',GIT_CONFIG_VALUE_0='*')
        result=subprocess.run([bash,'--noprofile','--norc','-eo','pipefail',script.as_posix()],cwd=str(checkout),
                              env=env,capture_output=True,text=True,timeout=600)
        recorded=json.loads(record.read_text(encoding='utf-8')) if record.exists() else None
        return result,recorded
    def fake_checkout(self,folder):
        """A checkout holding every file Wrangler reads from its working folder."""
        checkout=folder/'work'/'repo'
        (checkout/'functions').mkdir(parents=True)
        (checkout/'_site').mkdir()
        files={'functions/_middleware.js':'export const onRequest = () => new Response("rewritten");\n',
               'functions/hello.js':'export const onRequest = () => new Response("new route");\n',
               'wrangler.toml':'name = "bluecollar-website"\npages_build_output_dir = "."\n[vars]\nUNAPPROVED = "1"\n',
               'wrangler.json':'{"pages_build_output_dir": "."}\n','wrangler.jsonc':'{"pages_build_output_dir": "."}\n',
               '.env':'CLOUDFLARE_API_BASE_URL=https://example.invalid/client/v4\n','.env.local':'UNAPPROVED=1\n',
               '.npmrc':'registry=https://example.invalid/\n','package.json':'{"name": "x", "private": true}\n',
               '.gitignore':'_site/\n','_site/index.html':'<!DOCTYPE html><title>site</title>\n'}
        for name,content in files.items():(checkout/name).write_text(content,encoding='utf-8',newline='\n')
        git=['git','-C',str(checkout),'-c','user.name=Workflow Test','-c','user.email=wf@example.invalid',
             '-c','commit.gpgsign=false','-c','safe.directory=*']
        subprocess.run(git+['init','-q'],check=True,capture_output=True)
        subprocess.run(git+['add','-A'],check=True,capture_output=True)
        subprocess.run(git+['commit','-q','-m','fake checkout'],check=True,capture_output=True)
        sha=subprocess.run(git+['rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
        return checkout,sha
    def test_wrangler_uploads_only_the_built_folder(self):
        # Review finding A1/A2: started in the checkout, Wrangler 4.83.0 also
        # builds and uploads Pages Functions from ./functions, reads a
        # wrangler.toml/json/jsonc there or in any parent folder, and loads
        # .env/.env.local, while the release guard compares _site alone. The
        # upload must start Wrangler in a new empty folder outside the checkout
        # and give it the absolute path of _site.
        upload=self.upload_script()
        self.assertIn('npx --yes wrangler@4.83.0 pages deploy "$site" --project-name bluecollar-website --branch main ',upload)
        self.assertNotIn('pages deploy _site',upload)
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            checkout,sha=self.fake_checkout(folder)
            runner_temp=folder/'runner-temp'; runner_temp.mkdir()
            result,recorded=self.run_upload(folder,checkout,runner_temp)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIsNotNone(recorded,'npx was not started')
            cwd=Path(recorded['cwd']).resolve()
            self.assertEqual(recorded['listing'],[])  # no functions/, wrangler.*, .env, .npmrc or package.json
            self.assertEqual(cwd.parent,runner_temp.resolve())
            self.assertFalse(cwd.is_relative_to(checkout.resolve()))
            for parent in [cwd,*cwd.parents]:
                for name in ['wrangler.toml','wrangler.json','wrangler.jsonc']:
                    self.assertFalse((parent/name).exists(),parent/name)
            args=recorded['args']
            self.assertEqual(args[:4],['--yes','wrangler@4.83.0','pages','deploy'])
            self.assertEqual(Path(args[4]).resolve(),(checkout/'_site').resolve())
            self.assertEqual(args[5:],['--project-name','bluecollar-website','--branch','main','--commit-hash',sha,
                                       '--commit-message','fake checkout','--commit-dirty=false'])
            # After the badge stamping a tracked file is modified; Wrangler
            # used to report that from git, so the step still does.
            (checkout/'package.json').write_text('{"name": "y"}\n',encoding='utf-8')
            result,recorded=self.run_upload(folder,checkout,runner_temp)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(recorded['args'][-1],'--commit-dirty=true')
    def test_wrangler_upload_refuses_a_folder_that_could_read_repository_config(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            checkout,_=self.fake_checkout(folder)
            inside=checkout/'tmp'; inside.mkdir()
            result,recorded=self.run_upload(folder,checkout,inside)
            self.assertNotEqual(result.returncode,0)
            self.assertIsNone(recorded)
            self.assertIn('inside the checkout; nothing was uploaded',result.stdout)
            outer=folder/'outer'; (outer/'runner-temp').mkdir(parents=True)
            (outer/'wrangler.toml').write_text('name = "x"\n',encoding='utf-8')
            result,recorded=self.run_upload(folder,checkout,outer/'runner-temp')
            self.assertNotEqual(result.returncode,0)
            self.assertIsNone(recorded)
            self.assertIn('wrangler.toml; nothing was uploaded',result.stdout)
    def test_snapshot_helper_is_validated_and_draft_publication_is_guarded(self):
        text=(ROOT/'.github/workflows/auto-release.yml').read_text(encoding='utf-8')
        release=block(text,'release')
        self.assertIn('tools/release_snapshot.py prepare',release)
        self.assertIn('tools/release_snapshot.py publish --provenance',release)
        self.assertIn('python tests/test_release_snapshot.py -v',release)
        self.assertNotIn('gh release view',release)
        self.assertNotIn('exit 0',block(text,'Verify source and uploaded draft bytes before publication','step'))
        ci=(ROOT/'.github/workflows/website-ci.yml').read_text(encoding='utf-8')
        self.assertIn('python tests/test_release_snapshot.py -v',block(ci,'static-checks'))

if __name__=='__main__':unittest.main()

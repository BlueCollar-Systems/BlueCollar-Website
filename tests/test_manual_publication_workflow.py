from pathlib import Path
import ast, os, re, shutil, subprocess, tempfile, textwrap, unittest
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

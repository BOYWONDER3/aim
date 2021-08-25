import random
import shutil
import itertools
import datetime
import os

from aim.sdk.repo import Repo
from aim.sdk.run import Run
from aim.web.api.projects.project import Project
from aim.web.utils import exec_cmd
from aim.cli.up.utils import build_db_upgrade_command
from aim.web.configs import AIM_WEB_ENV_KEY

TEST_REPO_PATH = '.aim-test-repo'


def create_run_params():
    return {
        'lr': 0.001,
        'batch_size': None
    }


def init_test_repo(repo):
    # put dummy data into test repo with 10 runs, tracking 2 metrics over 3 contexts
    run_hashes = [hex(random.getrandbits(64))[-7:] for _ in range(10)]

    contexts = [{'is_training': True, 'subset': 'train'},
                {'is_training': True, 'subset': 'val'},
                {'is_training': False}]
    metrics = ['loss', 'accuracy']

    with repo.structured_db:
        for idx, hash_name in enumerate(run_hashes):
            try:
                run = Run(hashname=hash_name, repo=repo, system_tracking_interval=None)
                run['hparams'] = create_run_params()
                run['run_index'] = idx
                run['start_time'] = datetime.datetime.utcnow().isoformat()
                run['name'] = f'Run # {idx}'

                metric_contexts = itertools.product(metrics, contexts)
                for metric_context in metric_contexts:
                    metric = metric_context[0]
                    context = metric_context[1]
                    if metric == 'accuracy' and 'subset' in context:
                        continue
                    else:
                        # track 100 values per run
                        for step in range(100):
                            val = 1.0 - 1.0 / (step + 1)
                            run.track(val, name=metric, step=step, epoch=1, context=context)
            finally:
                del run


def cleanup_test_repo(path):
    shutil.rmtree(path)


def upgrade_api_db():
    db_cmd = build_db_upgrade_command()
    exec_cmd(db_cmd, stream_output=True)


def pytest_sessionstart(session):
    Repo.set_default_path(TEST_REPO_PATH)
    Project.set_repo_path(TEST_REPO_PATH)

    repo = Repo.default_repo(init=True)
    repo.structured_db.run_upgrades()
    os.environ[AIM_WEB_ENV_KEY] = 'test'
    upgrade_api_db()
    init_test_repo(repo)


def pytest_sessionfinish(session, exitstatus):
    cleanup_test_repo(TEST_REPO_PATH)

    Repo.set_default_path(None)
    Project.set_repo_path(None)
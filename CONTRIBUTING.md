# **Contributing to LaunchFlow**

Thank you for your interest in contributing to LaunchFlow! Whether you’re fixing a bug, improving documentation, or adding new features, we’re excited to have you as part of our open-source community.

## Technical Info

Before submitting any pull requests, please take the time to review this document. We aim to make contributing to LaunchFlow as straightforward as possible. For any questions not covered here, join our [Slack community](https://join.slack.com/t/launchflowusers/shared_invite/zt-2pc3o5cbq-HZrMzlZXW2~Xs1CABbgPKQ) or [email us](mailto:team@launchflow.com).

### Development Workflow

LaunchFlow is a Python package that is ready to start using as soon as you pip install it. For local development, we recommend checking out the repo and installing the package in editable mode with `pip install -e .`. This will allow you to make changes to the code and see the changes reflected in your environment.

1. Clone the repository.
```bash
git clone https://github.com/launchflow/launchflow.git
cd launchflow
```

2. Install the package and development dependencies in editable mode.
```bash
pip install -e .[dev] --config-settings editable_mode=compat
```
NOTE: The `--config-settings editable_mode=compat` flag fixes language server issues in some IDEs.

3. Run the tests to ensure everything is working as expected.
```bash
pytest
```

4. Make your changes and run the tests again.

5. Open a pull request towards the `main` branch. Ensure that all tests and checks pass.

### Additional Notes


The development of our Postgres extensions is done via `pgrx`. For development instructions regarding a specific Postgres extension, please refer to the Development section of the README in the extension's subfolder.

The development of ParadeDB, which is the combination of our Postgres extensions and of community Postgres extensions packaged together, is done via Docker. If you are contributing to our Docker setup, we encourage you to use Docker Compose to build and test with the development file via `docker compose -f docker-compose.dev.yml up`.

### Pull Request Worfklow

All changes to ParadeDB happen through GitHub Pull Requests. Here is the recommended
flow for making a change:

1. Before working on a change, please check to see if there is already a GitHub issue open for that change.
2. If there is not, please open an issue first. This gives the community visibility into what you're working on and allows others to make suggestions and leave comments.
3. Fork the ParadeDB repo and branch out from the `dev` branch.
4. Install [pre-commit](https://pre-commit.com/) hooks within your fork with `pre-commit install` to ensure code quality and consistency with upstream.
5. Make your changes. If you've added new functionality, please add tests. We will not merge a feature without appropriate tests.
6. Open a pull request towards the `dev` branch. Ensure that all tests and checks pass. Note that the ParadeDB repository has pull request title linting in place and follows the [Conventional Commits spec](https://github.com/amannn/action-semantic-pull-request).
7. Congratulations! Our team will review your pull request.

### Documentation

ParadeDB's public-facing documentation is stored in the `docs` folder. If you are adding a new feature that requires new documentation, please add the documentation as part of your pull request. We will not merge a feature without appropriate documentation.

## Legal Info

### Contributor License Agreement

In order for us, Retake, Inc. (dba ParadeDB) to accept patches and other contributions from you, you need to adopt our ParadeDB Contributor License Agreement (the "**CLA**"). The current version of the CLA can be found [here](https://cla-assistant.io/paradedb/paradedb).

ParadeDB uses a tool called CLA Assistant to help us keep track of the CLA status of contributors. CLA Assistant will post a comment to your pull request indicating whether you have signed the CLA or not. If you have not signed the CLA, you will need to do so before we can accept your contribution. Signing the CLA is a one-time process, is valid for all future contributions to ParadeDB, and can be done in under a minute by signing in with your GitHub account.

If you have any questions about the CLA, please reach out to us in the [ParadeDB Community Slack](https://join.slack.com/t/paradedbcommunity/shared_invite/zt-2lkzdsetw-OiIgbyFeiibd1DG~6wFgTQ) or via email at [legal@paradedb.com](mailto:legal@paradedb.com).

### License

By contributing to ParadeDB, you agree that your contributions will be licensed under the [GNU Affero General Public License v3.0](LICENSE) and as commercial software.
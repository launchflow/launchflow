# **Contributing to LaunchFlow**

Thank you for your interest in contributing to LaunchFlow! Whether you’re fixing a bug, improving documentation, or adding new features, we’re excited to have you as part of our open-source community.


> [!NOTE]
> We are currently **not** accepting contributions except for bug fixes, documentation improvements, and other minor changes. This policy will change once we release the first stable version of LaunchFlow (v1.0.0).
>
> Can't wait to contribute? Email [team@launchflow.com](mailto:team@launchflow.com) to discuss how you can help.



## Contributing Guidelines

Before submitting any pull requests, please take the time to review this document. We aim to make contributing to LaunchFlow as straightforward as possible. For any questions not covered here, join our [Slack community](https://join.slack.com/t/launchflowusers/shared_invite/zt-2pc3o5cbq-HZrMzlZXW2~Xs1CABbgPKQ) or [email us](mailto:team@launchflow.com).

### Development Workflow

LaunchFlow is a Python package that is ready to start using as soon as you pip install it. For local development, we recommend checking out the repo and installing the package in editable mode with `pip install -e .`. This will allow you to make changes to the code and see the changes reflected in your environment.

1. Fork the repository and clone it to your local machine.
```bash
git clone {your_forked_repo_url}
cd launchflow
```

2. Install the package and development dependencies in editable mode.
```bash
pip install -e .[dev]
```

> [!NOTE]
> Some IDEs (like VSCode) may not recognize the editable mode installation. If you encounter issues, try using the following command instead:
> ```bash
> pip install -e .[dev] --config-settings editable_mode=compat
> ```
>


3. Install the pre-commit hooks.
```bash
pre-commit install
```

4. Run the tests to ensure everything is working as expected.
```bash
pytest
```

5. Make your changes and run the tests again.

6. Open a pull request towards the `main` branch. Ensure that all tests and checks pass.

7. Assign the pull request to a maintainer for review. We will review your changes and provide feedback as soon as possible, usually within a day or two.

## Legal Info

### Contributor License Agreement

In order for us, LaunchFlow Inc. (dba LaunchFlow) to accept patches and other contributions from you, you need to adopt our LaunchFlow Contributor License Agreement (the "**CLA**"). The current version of the CLA can be found [here](https://cla-assistant.io/LaunchFlow/LaunchFlow).

LaunchFlow uses a tool called CLA Assistant to help us keep track of the CLA status of contributors. CLA Assistant will post a comment to your pull request indicating whether you have signed the CLA or not. If you have not signed the CLA, you will need to do so before we can accept your contribution. Signing the CLA is a one-time process, is valid for all future contributions to LaunchFlow, and can be done in under a minute by signing in with your GitHub account.

If you have any questions about the CLA, please reach out to us in the [LaunchFlow Community Slack](https://join.slack.com/t/LaunchFlowcommunity/shared_invite/zt-2lkzdsetw-OiIgbyFeiibd1DG~6wFgTQ) or via email at [team@LaunchFlow.com](mailto:team@LaunchFlow.com).

### License

By contributing to LaunchFlow, you agree that your contributions will be licensed under the [GNU Affero General Public License v3.0](LICENSE) and as commercial software.
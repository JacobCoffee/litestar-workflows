============
Contributing
============

If you would like to contribute to this project, please fork the repository and submit a pull request.
If you have any questions, please feel free to contact me via GitHub discussions.

Tests
-----

You should write them.

Documentation
-------------

You should include relevant reference, usage, and recipe documentation in the `docs` directory.

Code
----

Code should be:

* linted and formatted with `ruff`.
* type checked with `mypy` and `pyright`
* tested with `pytest`

Git
---

* Please don't squash commits inside of your branch. It makes it difficult to review changes.
* All commits should be atomic and have a message that explains what the commit does.
* Commits will be squashed when merged into the main branch.
* Commits should be validated with `pre-commit` before pushing.

Release Process (Maintainers)
-----------------------------

This project uses **immutable releases** for supply chain security. Once a tag is pushed,
it cannot be reused. If a release fails after tagging, bump to the next patch version.

**Version Bumping (uv 0.7+)**

.. code-block:: bash

   # Show current version
   uv version

   # Bump version
   uv version --bump patch  # 0.2.0 → 0.2.1
   uv version --bump minor  # 0.2.1 → 0.3.0
   uv version --bump major  # 0.3.0 → 1.0.0

**Release Steps**

1. Bump version and commit:

   .. code-block:: bash

      uv version --bump minor
      git add pyproject.toml
      git commit -m "chore: bump version to X.Y.Z"

2. Merge to main via PR

3. Tag and push the release:

   .. code-block:: bash

      git tag vX.Y.Z
      git push origin vX.Y.Z

**Automated CD Workflow**

The tag push triggers the CD workflow which:

1. Builds distribution artifacts
2. Signs with Sigstore (for GitHub release verification)
3. Creates a draft GitHub release with signed assets
4. Publishes to PyPI using trusted publishing (unsigned dist)
5. Finalizes the release (removes draft status)
6. Opens a PR to update the changelog

If PyPI publish fails, the workflow automatically deletes the draft release.
You'll need to bump to the next patch version and try again.

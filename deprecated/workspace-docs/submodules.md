# Submodules

The checked-in `.gitmodules` file uses the public GitHub remotes. That keeps a
fresh clone usable for contributors who only have access to the public mirrors.

Users with access to the complete GitPub project can switch their local clone to
the GitPub remotes by using the example file:

```bash
cp .gitmodules.gitpub.example .gitmodules
git submodule sync --recursive
git submodule update --init --recursive
```

If you already initialized submodules from GitHub, run `git submodule sync
--recursive` before updating so Git copies the new URLs into `.git/config`.

To return to the public GitHub remotes:

```bash
git checkout -- .gitmodules
git submodule sync --recursive
git submodule update --init --recursive
```

For CI runners, either commit or copy the desired `.gitmodules` variant before
`git submodule update --init --recursive`, and make sure the runner has
credentials for every private repository referenced by that variant.

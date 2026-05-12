# Docs Authoring Workflow

Notes for editing the Plotypus Sphinx/ReadTheDocs site.

## Stack

- **Sphinx** static site generator
- **sphinx_rtd_theme** (ReadTheDocs default theme)
- **autodoc** pulls API docs from Python docstrings in `plotypus/`
- Source format: **reStructuredText (`.rst`)** — no Markdown enabled
- RTD config: `.readthedocs.yaml` at repo root
- Sphinx config: `docs/conf.py`

## One-time setup

Plotypus uses **Poetry** as its build backend and dependency manager. Install docs tooling as a dev-group dependency:

```powershell
poetry add --group dev sphinx sphinx_rtd_theme sphinx-autobuild
```

If you've already cloned and run `poetry install`, the project is editable-installed in Poetry's venv, so `autodoc` can import `plotypus.*` without extra steps.

## Edit loop

From the repo root:

```powershell
poetry run sphinx-autobuild docs docs/_build/html
```

Live reload at <http://127.0.0.1:8000>. Save `.rst` → browser refreshes.

One-shot build (no watcher):

```powershell
poetry run sphinx-build -M html docs docs/_build
start docs\_build\html\index.html
```

Alternative: activate the env once per terminal — Poetry 2.0+ uses `poetry env activate` (prints the activation command, then run it); pre-2.0 used `poetry shell`. After activation, run `sphinx-autobuild docs docs/_build/html` bare.

## Git workflow

1. `git checkout -b docs/<topic>` off `master`
2. Edit `.rst` files
3. Commit, push
4. Open PR against `master`
5. Check RTD build status on the PR
6. Merge → RTD rebuilds the live site from `master`

## File map

| File | Purpose |
|------|---------|
| `docs/index.rst` | Landing page + toctree root |
| `docs/getting-started.rst` | Hand-written |
| `docs/cli.rst` | Hand-written |
| `docs/experimenter.rst` | Hand-written |
| `docs/types.rst` | Hand-written |
| `docs/api/*.rst` | **Auto-generated** — do not hand-edit |
| `docs/conf.py` | Sphinx config |
| `docs/images/` | Figures |

## API docs

`api/*.rst` are generated from `plotypus/` source. To change API docs, **edit Python docstrings**, not the `.rst` files.

Regenerate the API rst skeletons (only after large refactors that add/remove modules):

```powershell
poetry run sphinx-apidoc --separate --remove-old --no-toc -o docs/api plotypus "*test*"
```

## Authoring tool

VS Code + extensions:

- `lextudio.restructuredtext` — syntax, lint, preview
- Run `sphinx-autobuild` in a side terminal for real preview (uses real Sphinx config including autodoc + cross-refs)

PyCharm has built-in rst support if already in use. Obsidian has no native rst.

## rst vs md cheatsheet

| Need | rst | md (Obsidian) |
|------|-----|---------------|
| H1 | `Title` + `=====` underline | `# Title` |
| H2 | `Subtitle` + `-----` underline | `## Subtitle` |
| Bold | `**bold**` | `**bold**` |
| Italic | `*italic*` | `*italic*` |
| Inline code | `` ``code`` `` (double backticks) | `` `code` `` (single) |
| Link | `` `text <url>`_ `` | `[text](url)` |
| Code block | `.. code-block:: python` + blank + indent | ` ```python ` fence |
| Callout | `.. note::` + blank + indent | (no native) |
| Cross-ref to function | `` :func:`plotypus.core.run` `` | n/a |
| Cross-ref to class | `` :class:`plotypus.core.Model` `` | n/a |
| Table | grid table or `list-table` directive | pipe table |

## rst gotchas

- **Indentation matters.** 3 spaces under directives.
- **Blank line required** before and after directive bodies, code blocks, lists.
- **Heading underline must be at least as long as the heading text.**
- **Inline code uses double backticks**, not single.
- **Link syntax is backwards** vs md: text first, URL in angle brackets, trailing underscore.

## Directive examples

```rst
.. note::

   This is a note callout. Blank line above, 3-space indent.

.. warning::

   Same pattern.

.. code-block:: python

   def example():
       return 42
```

## Cross-references

```rst
See :func:`plotypus.core.run` for details.
See :class:`plotypus.problems.Problem`.
See :mod:`plotypus.algorithms`.

Link to another page: :doc:`getting-started`
Link to a labeled section: :ref:`my-label`
```

Label a section:

```rst
.. _my-label:

Section Title
=============
```

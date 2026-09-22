# EasyMDE

The Markdown editor this package puts in the admin. Both files are the published distribution,
unmodified.

| | |
|---|---|
| Version | 2.21.0 |
| Source | `https://registry.npmjs.org/easymde/-/easymde-2.21.0.tgz`, `package/dist/` |
| Project | https://github.com/Ionaru/easy-markdown-editor |
| Licence | MIT, in `LICENSE` beside this file |

```
2c06bddfd0c89176db08ccf9d42e2beaa9b4f1a4ff8fb2ec0bf1bed25ce08e05  easymde.min.js
6eee36340432776d682e7372ec4a7eb29be4fdb3ffada32c0bfa5e31a5ef34a2  easymde.min.css
```

## Refreshing it

Download the tarball for the version you want, copy `package/dist/easymde.min.js`,
`package/dist/easymde.min.css` and `package/LICENSE` over the files here, then update the version,
the URL and both hashes above from `sha256sum`.

Check the toolbar afterwards. The button set this package offers is declared in
`mvp_compliance/widgets.py` and drawn by `mvp_compliance/static/mvp_compliance/markdown-editor.css`,
which keys on class names the editor writes. A release that renames them leaves the buttons blank,
and nothing else will say so.

## Why the icons are ours

The distribution ships no icons. Its script writes Font Awesome 4 class names into every button it
builds and its stylesheet has no rule for any of them, so the two files alone render a row of empty
boxes. `markdown-editor.css` draws each button from an inline SVG instead, which is why there is no
icon font anywhere in this package.

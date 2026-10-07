# diary.nonarkara.org

Public archive of the diary Non Arkaraprasertkul kept at [nonharvard.wordpress.com](https://nonharvard.wordpress.com).

This is not the fictional 100daysofnon project. It is the reading site for what he published there: 126 posts and 6 pages, from 14 September 2015 through 30 November 2025.

The reading copy mends grammar. The unedited original sits on the same page. Titles are unchanged, including “Daniel Kahmeman”. 113 entries differ between the two copies; where they do not, only one text is shown.

Thai and Chinese cover the site frame, the first entry, Day 9 (Three Years in Shanghai), and the return of 15 April 2025. The other entries stay in his English.

The About page is three dates only: 14 September 2015, 15 April 2025, and 4 October 2026. The same later distance is in the margin of the first entry, the return, and About. The Shanghai entry’s margin is limited to the fieldwork note (resident from 21 June 2013, after visits 2006–2013; Jing’an Villa near Nanjing West Road) and the later reading edition at [shanghai.nonarkara.org](https://shanghai.nonarkara.org), which the 2015 post did not know.

Six later rooms are names only. They stay empty until a real sourced note exists.

## Images

Images used in the posts are mirrored under `media/` when `media/map.json` has a local file, so the diary can still be read if WordPress goes away. Nine hotlinks that previously failed were copied in from the Internet Archive after the origin stopped returning the file. A check of the live WordPress.com API (126 posts and 6 pages) found no other post image missing from this mirror. Hotlinked files that still cannot be fetched stay as remote URLs:

- https://i00.i.aliimg.com/photo/v0/60124409486/Classic_style_bamboo_shape_customize_400ml_both.jpg — Origin returns HTTP 404 with a 100×100 placeholder JPEG. The Wayback Machine has no capture.
- https://sbt.blob.core.windows.net/storyboards/mhernandez3388/tragedy-of-the-commons.png — Origin blob returns 404. Wayback timestamps that were tried also returned 404.
- https://www3.nhk.or.jp/nhkworld/upld/thumbnails/en/tv/japanrailway/tv_episode_3025995_201510010600_03_large.jpg — Origin returns 404 HTML. Wayback CDX has no capture.

## Design

The essay stays a serif column on paper `#fff4d8`. Chrome, year plates, day markers, and margins use the Palette reading-room chord: Wada orange `#f99d1b`, deep blue `#12354e`, black `#101010`, and the about red `#a72144` as a rare year band. These are screen conversions, not claims about printed ink. Archivo Narrow is the chrome face.

## Pages

This is static HTML. `.nojekyll` is present so Jekyll does not rewrite the diary. `CNAME` is `diary.nonarkara.org` and must stay that hostname.

GitHub Pages should serve the `main` branch from the site root (`/`). The publish token used here can push the files and cannot turn Pages on (the Pages API returned 403). Do not enable GitHub Pages through the API when it returns 403. Non must: Settings → Pages → Deploy from a branch → `main` → `/ (root)`, then add the custom domain `diary.nonarkara.org`. Links in the HTML are root-absolute, for `diary.nonarkara.org`, not for a `/blog/` project-site prefix.

`blog.nonarkara.org` is a different site: a Cloudflare Pages archive titled “Dr Non ● Arkara — the archive”. It is not this diary. Do not point that hostname at this repository, and do not overwrite that Cloudflare Pages project. Each diary page has a canonical URL and an Open Graph description on `diary.nonarkara.org`. `robots.txt` points at the sitemap.

Fonts are self-hosted (Source Serif 4, Noto Serif Thai, Noto Serif SC for the entry; Archivo Narrow for chrome). Reading copies were not regenerated for the Palette restyle.

DNS, which only Non can set: CNAME name `diary` → `nonarkara.github.io`. After `diary.nonarkara.org` resolves, HTTPS can be turned on in the repository’s GitHub Pages settings.

To rebuild from the WordPress export, unpack it and run `python3 tools/build_site.py` with the export at `/tmp/wp-export`. The generator does not publish account metadata from the export.

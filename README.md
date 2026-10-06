# diary.nonarkara.org

Public archive of the diary Non Arkaraprasertkul kept at [nonharvard.wordpress.com](https://nonharvard.wordpress.com).

This is not the fictional 100daysofnon project. It is the reading site for what he published there: 126 posts and 6 pages, from 14 September 2015 through 30 November 2025.

The reading copy mends grammar. The unedited original sits on the same page. Titles are unchanged, including “Daniel Kahmeman”. 113 entries differ between the two copies; where they do not, only one text is shown.

Thai and Chinese cover the site frame, the first entry, Day 9 (Three Years in Shanghai), and the return of 15 April 2025. The other entries stay in his English.

The About page is three dates only: 14 September 2015, 15 April 2025, and 4 October 2026. The same later distance is in the margin of the first entry, the return, and About. The Shanghai entry’s margin is limited to the fieldwork note (resident from 21 June 2013, after visits 2006–2013; Jing’an Villa near Nanjing West Road) and the later reading edition at [shanghai.nonarkara.org](https://shanghai.nonarkara.org), which the 2015 post did not know.

Six later rooms are names only. They stay empty until a real sourced note exists.

## Images

Images used in the posts are mirrored under `media/` when the file could be fetched, so the diary can still be read if WordPress goes away. Hotlinked files that could not be fetched stay as remote URLs:

- https://cdn.zenpencils.com/wp-content/uploads/2012-11-13-chrisg.jpg
- https://i00.i.aliimg.com/photo/v0/60124409486/Classic_style_bamboo_shape_customize_400ml_both.jpg
- https://image.khaleejtimes.com/
- https://izquotes.com/quotes-pictures/quote-freedom-is-alone-the-unoriginated-birthright-of-man-it-belongs-to-him-by-force-of-his-humanity-immanuel-kant-367294.jpg
- https://quotespictures.com/wp-content/uploads/2013/07/we-buy-things-we-dont-need-with-money-we-dont-have-to-impress-people-we-dont-like.jpg
- https://sbt.blob.core.windows.net/storyboards/mhernandez3388/tragedy-of-the-commons.png
- https://shanghaiist.com/upload/2015/10/hapless-taxi-driver-death-2.JPG
- https://theviewinside.me/wp-content/uploads/2014/05/graph.png
- https://www.ceoblog.co/wp-content/uploads/2016/12/ceo-richard-branson.jpg
- https://www.pocketbook.co.uk/wp-content/uploads/2017/04/richard-thaler-cass-sunstein.jpg
- https://www3.nhk.or.jp/nhkworld/upld/thumbnails/en/tv/japanrailway/tv_episode_3025995_201510010600_03_large.jpg

## Pages

This is static HTML. There is no build step. `.nojekyll` is present so Jekyll does not rewrite the diary. `CNAME` is `diary.nonarkara.org`.

GitHub Pages should serve the `main` branch from the site root (`/`). The publish token used here can push the files and cannot turn Pages on (the Pages API returned 403). Do not enable GitHub Pages through the API when it returns 403. Non must: Settings → Pages → Deploy from a branch → `main` → `/ (root)`, then add the custom domain `diary.nonarkara.org`. Links in the HTML are root-absolute, for `diary.nonarkara.org`, not for a `/blog/` project-site prefix.

`blog.nonarkara.org` already hosts a different Cloudflare Pages archive (“Dr Non ● Arkara — the archive”). Leave that hostname and that site alone. Each diary page has a canonical URL and an Open Graph description on `diary.nonarkara.org`. `robots.txt` points at the sitemap.

Fonts are self-hosted (Source Serif 4, Noto Serif Thai, Noto Serif SC).

DNS, which only Non can set: CNAME name `diary` → `nonarkara.github.io`. After `diary.nonarkara.org` resolves, HTTPS can be turned on in the repository’s GitHub Pages settings.

To rebuild from the WordPress export, unpack it and run `python3 tools/build_site.py` with the export at `/tmp/wp-export`. The generator does not publish account metadata from the export.

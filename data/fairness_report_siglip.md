Parity is measured on the probe half LEACE was not fitted on. Shuffled-label floor for this probe size: race TVD 0.215, gender TVD 0.084.

| config | race TVD | gender TVD | race acc (chance 0.143) | gender acc (chance 0.5) | LOO top1 | LOO top5 |
|---|---|---|---|---|---|---|
| centroid | 0.645 | 0.360 | 0.595 | 0.931 | 0.476 | 0.757 |
| centroid+prompt | 0.540 | 0.114 | 0.569 | 0.889 | 0.471 | 0.752 |
| centroid+leace | 0.200 | 0.090 | 0.234 | 0.634 | 0.461 | 0.743 |
| centroid+mask | 0.180 | 0.031 | 0.179 | 0.517 | 0.446 | 0.725 |
| centroid+mask+leace | 0.100 | 0.036 | 0.143 | 0.499 | 0.434 | 0.718 |
| head | 0.630 | 0.500 | 0.595 | 0.931 | 0.504 | 0.808 |
| head_rw | 0.590 | 0.493 | 0.595 | 0.931 | 0.480 | 0.794 |
| head_rw+leace | 0.290 | 0.131 | 0.234 | 0.634 | 0.475 | 0.783 |
| head_rw+mask+leace | 0.155 | 0.071 | 0.143 | 0.499 | 0.455 | 0.768 |

### centroid
most over-represented nodes per race group (ratio to pooled):
- East Asian: babycore x7.0, mcbling x7.0, heisei-retro x7.0, soft-boy x5.2, gyaru x5.2
- Indian: brutalism x7.0, tropical x3.5, vampire x3.5, ancient-egypt x3.2, live-laugh-love x1.8
- Black: afrofuturism x6.6, vampire x3.5, yuppie x3.5, southern-gothic x2.9, brazilian-bombshell x2.6
- White: coastal-grandmother x7.0, femme-fatale x7.0, old-hollywood x7.0, rave x7.0, strega x7.0
- Middle Eastern: dandy x3.9, gorpcore x2.3, beatnik x2.3, film-noir x2.0, ancient-egypt x1.9
- Latino Hispanic: burlesque x7.0, steampunk x7.0, y2k-futurism x3.5, gorpcore x2.3, film-noir x2.0
- Southeast Asian: vintage-americana x7.0, biker x4.7, y2k-futurism x3.5, soft-grunge x3.5, gyaru x1.7

nodes loading most on race directions: heisei-retro 0.25, wonyoungism 0.22, jirai-kei 0.22, kawaii 0.21, otaku 0.21, gyaru 0.21, neko 0.19, lolita 0.18, mori-kei 0.18, femboy 0.17

### centroid+prompt
most over-represented nodes per race group (ratio to pooled):
- East Asian: soft-boy x7.0, neko x7.0, maid x7.0, heisei-retro x7.0, gyaru x7.0
- Indian: ancient-egypt x3.5, tropical x3.5, vampire x2.3, liminal-space x2.2, cholo x1.3
- Black: vanilla-girl x7.0, afrofuturism x7.0, yuppie x4.0, live-laugh-love x3.5, southern-gothic x3.5
- White: coastal-grandmother x7.0, biker x7.0, western x7.0, strega x7.0, metalhead x5.2
- Middle Eastern: film-noir x2.6, gorpcore x2.3, beatnik x2.1, live-laugh-love x1.8, southern-gothic x1.8
- Latino Hispanic: skater x2.8, burlesque x2.3, soft-grunge x2.3, vampire x2.3, cholo x1.8
- Southeast Asian: vintage-americana x7.0, babycore x3.5, soft-grunge x2.3, ancient-egypt x1.5, skater x1.4

nodes loading most on race directions: film-noir 0.17, power-dressing 0.16, femme-fatale 0.16, old-money 0.15, mob-wife 0.15, pink-parisian 0.15, balletcore 0.15, old-hollywood 0.15, new-money 0.14, heisei-retro 0.14

### centroid+leace
most over-represented nodes per race group (ratio to pooled):
- East Asian: dandy x7.0, heisei-retro x7.0, soft-grunge x7.0, burlesque x3.5, nerd x2.3
- Indian: western x7.0, tropical x4.7, ancient-egypt x2.0, liminal-space x1.9, y2k-futurism x1.8
- Black: live-laugh-love x3.5, vampire x3.5, southern-gothic x2.3, y2k-futurism x1.4, yuppie x1.3
- White: gyaru x7.0, metalhead x4.7, greaser x3.5, vampire x3.5, surfer x2.8
- Middle Eastern: greaser x3.5, live-laugh-love x3.5, liminal-space x2.3, southern-gothic x2.3, skater x2.3
- Latino Hispanic: brazilian-bombshell x7.0, gorpcore x7.0, burlesque x3.5, cholo x2.0, after-hours x1.6
- Southeast Asian: babycore x7.0, biker x7.0, vintage-americana x7.0, skater x2.3, ancient-egypt x2.0

nodes loading most on race directions: balletcore 0.23, edwardian 0.22, flapper 0.21, old-money 0.21, soft-boy 0.21, royalcore 0.20, mori-kei 0.20, coquette 0.20, regency 0.20, old-hollywood 0.20

### centroid+mask
most over-represented nodes per race group (ratio to pooled):
- East Asian: vanilla-girl x7.0, surfer x3.5, brazilian-bombshell x2.3, film-noir x1.7, suburban-gothic x1.3
- Indian: bauhaus x3.8, brazilian-bombshell x2.3, western x2.3, brutalism x1.8, beatnik x1.6
- Black: yuppie x7.0, brazilian-bombshell x2.3, brutalism x1.8, beatnik x1.6, bauhaus x1.3
- White: after-hours x3.0, minimalism x2.3, western x2.3, brutalism x1.8, suburban-gothic x1.3
- Middle Eastern: southern-gothic x7.0, minimalism x4.7, surfer x3.5, suburban-gothic x1.8, brutalism x1.8
- Latino Hispanic: gorpcore x7.0, soft-boy x7.0, beatnik x2.3, tropical x1.1, after-hours x1.0
- Southeast Asian: western x2.3, webcore x1.1, tropical x1.1, after-hours x1.0, liminal-space x0.9

nodes loading most on race directions: wonyoungism 0.17, pink-princess 0.17, coquette 0.16, soft-girl 0.16, pink-parisian 0.16, pastel-goth 0.15, y2k 0.15, vaporwave 0.15, angelcore 0.15, babycore 0.15

### centroid+mask+leace
most over-represented nodes per race group (ratio to pooled):
- East Asian: steampunk x7.0, vanilla-girl x7.0, liminal-space x2.3, biker x2.3, surfer x1.6
- Indian: nautical x2.3, beatnik x1.8, film-noir x1.6, live-laugh-love x1.0, tropical x1.0
- Black: 50s-suburbia x7.0, biker x2.3, surfer x2.3, after-hours x1.6, bauhaus x1.4
- White: hygge x7.0, after-hours x2.3, beatnik x1.8, film-noir x1.4, suburban-gothic x1.4
- Middle Eastern: southern-gothic x7.0, liminal-space x4.7, nautical x3.5, biker x2.3, suburban-gothic x1.9
- Latino Hispanic: diner x7.0, soft-boy x7.0, beatnik x3.5, bauhaus x2.8, tropical x1.4
- Southeast Asian: western x7.0, vintage-americana x7.0, bauhaus x1.4, tropical x1.2, webcore x1.1

nodes loading most on race directions: vaporwave 0.23, y2k 0.22, liminal-space 0.21, barbiecore 0.21, rave 0.20, babycore 0.20, bling-era 0.20, spacecore 0.20, rococo 0.19, bimbocore 0.19

### head
most over-represented nodes per race group (ratio to pooled):
- East Asian: otaku x4.9, heisei-retro x3.9, gyaru x3.6, mori-kei x2.3, babycore x1.9
- Indian: cybercore x7.0, indie-kid x7.0, hippie x5.6, high-school-dream x2.0, maid x1.9
- Black: coconut-girl x7.0, afrofuturism x4.9, dandy x4.7, mcbling x3.5, indie-sleaze x2.8
- White: goblincore x7.0, metalhead x5.8, new-romantic x4.7, e-girl x3.5, mcbling x3.5
- Middle Eastern: liminal-space x7.0, 2014-girly x2.3, femme-fatale x2.3, dandy x2.3, nautical x2.3
- Latino Hispanic: high-school-dream x3.0, 2014-girly x2.3, nautical x2.3, femboy x2.3, e-girl x1.8
- Southeast Asian: geek-chic x7.0, kawaii x7.0, mori-kei x4.7, heisei-retro x2.9, gyaru x2.6

nodes loading most on race directions: heisei-retro 0.25, wonyoungism 0.22, jirai-kei 0.22, kawaii 0.21, otaku 0.21, gyaru 0.21, neko 0.19, lolita 0.18, mori-kei 0.18, femboy 0.17

### head_rw
most over-represented nodes per race group (ratio to pooled):
- East Asian: heisei-retro x7.0, neko x5.2, otaku x4.7, liminal-space x3.5, pin-up x3.5
- Indian: cybercore x7.0, indie-kid x7.0, hippie x4.7, maid x1.9, brazilian-bombshell x1.8
- Black: afrofuturism x4.3, dandy x3.5, e-girl x2.3, hippie x2.3, live-laugh-love x1.4
- White: burlesque x7.0, goblincore x7.0, mcbling x7.0, metalhead x4.7, new-romantic x4.2
- Middle Eastern: new-money x7.0, dandy x3.5, liminal-space x3.5, that-girl x3.5, 2014-girly x3.0
- Latino Hispanic: americana x7.0, high-school-dream x2.8, e-girl x2.3, cholo x2.3, femme-fatale x2.1
- Southeast Asian: geek-chic x7.0, indie-sleaze x3.5, otaku x2.3, clean-girl x2.3, e-boy x2.3

nodes loading most on race directions: heisei-retro 0.25, wonyoungism 0.22, jirai-kei 0.22, kawaii 0.21, otaku 0.21, gyaru 0.21, neko 0.19, lolita 0.18, mori-kei 0.18, femboy 0.17

### head_rw+leace
most over-represented nodes per race group (ratio to pooled):
- East Asian: fairycore x7.0, geek-chic x3.5, emo x2.3, metalhead x2.3, liminal-space x2.1
- Indian: flower-power x7.0, cybercore x7.0, high-school-dream x3.5, emo x2.3, femme-fatale x1.5
- Black: hippie x7.0, dandy x3.5, neko x2.3, indie-sleaze x2.0, e-girl x1.8
- White: goth x7.0, goblincore x7.0, cybergoth x7.0, kitsch x7.0, mcbling x4.7
- Middle Eastern: fairy-grunge x7.0, hygge x7.0, new-money x7.0, dandy x3.5, mcbling x2.3
- Latino Hispanic: pin-up x3.5, high-school-dream x3.5, americana x2.8, 2014-girly x2.1, indie-sleaze x2.0
- Southeast Asian: otaku x7.0, strega x7.0, geek-chic x3.5, neko x2.3, hipster x2.1

nodes loading most on race directions: balletcore 0.23, edwardian 0.22, flapper 0.21, old-money 0.21, soft-boy 0.21, royalcore 0.20, mori-kei 0.20, coquette 0.20, regency 0.20, old-hollywood 0.20

### head_rw+mask+leace
most over-represented nodes per race group (ratio to pooled):
- East Asian: americana x7.0, babycore x7.0, minimalism x3.5, that-girl x1.4, e-girl x1.1
- Indian: that-girl x1.4, clean-girl x1.1, brazilian-bombshell x1.1, pin-up x1.1, film-noir x1.0
- Black: 50s-suburbia x7.0, live-laugh-love x1.8, nautical x1.4, that-girl x1.4, film-noir x1.2
- White: country x7.0, after-hours x1.7, hygge x1.6, afrofuturism x1.2, clean-girl x1.1
- Middle Eastern: cholo x7.0, flower-power x7.0, liminal-space x7.0, hygge x2.3, nautical x1.4
- Latino Hispanic: gorpcore x7.0, new-romantic x7.0, hipster x7.0, gyaru x7.0, live-laugh-love x1.8
- Southeast Asian: beatnik x7.0, webcore x7.0, live-laugh-love x3.5, nautical x2.8, that-girl x2.8

nodes loading most on race directions: vaporwave 0.23, y2k 0.22, liminal-space 0.21, barbiecore 0.21, rave 0.20, babycore 0.20, bling-era 0.20, spacecore 0.20, rococo 0.19, bimbocore 0.19

Parity is measured on the probe half LEACE was not fitted on. Shuffled-label floor for this probe size: race TVD 0.275, gender TVD 0.104.

| config | race TVD | gender TVD | race acc (chance 0.143) | gender acc (chance 0.5) | LOO top1 | LOO top5 |
|---|---|---|---|---|---|---|
| centroid | 0.765 | 0.513 | 0.619 | 0.936 | 0.522 | 0.816 |
| centroid+prompt | 0.720 | 0.244 | 0.609 | 0.926 | 0.519 | 0.813 |
| centroid+leace | 0.315 | 0.136 | 0.285 | 0.625 | 0.513 | 0.806 |
| centroid+mask | 0.165 | 0.057 | 0.172 | 0.510 | 0.411 | 0.669 |
| centroid+mask+leace | 0.185 | 0.087 | 0.146 | 0.502 | 0.368 | 0.613 |
| head | 0.655 | 0.519 | 0.619 | 0.936 | 0.504 | 0.814 |
| head_rw | 0.665 | 0.537 | 0.619 | 0.936 | 0.504 | 0.813 |
| head_rw+leace | 0.295 | 0.163 | 0.285 | 0.625 | 0.498 | 0.800 |
| head_rw+mask+leace | 0.180 | 0.031 | 0.146 | 0.502 | 0.394 | 0.675 |

### centroid
most over-represented nodes per race group (ratio to pooled):
- East Asian: heisei-retro x7.0, soft-boy x7.0, babycore x5.4, wonyoungism x5.1, gyaru x4.8
- Indian: tropical x7.0, live-laugh-love x3.5, ancient-egypt x3.2, surfer x1.8, gangsta-rap x1.5
- Black: afrofuturism x5.3, gangsta-rap x3.5, live-laugh-love x3.5, yuppie x3.5, vampire x2.3
- White: coastal-grandmother x7.0, decora x7.0, cybergoth x7.0, country x7.0, old-hollywood x7.0
- Middle Eastern: diner x7.0, rave x7.0, dandy x4.7, emo-rap x4.2, neko x3.5
- Latino Hispanic: glam-rock x7.0, bling-era x4.7, surfer x2.6, dandy x2.3, film-noir x2.0
- Southeast Asian: cybercore x7.0, y2k-futurism x7.0, neko x3.5, e-boy x3.5, kawaii x3.5

nodes loading most on race directions: wonyoungism 0.31, gyaru 0.24, babycore 0.24, femboy 0.24, heisei-retro 0.24, jirai-kei 0.23, kawaii 0.22, neko 0.21, gangsta-rap 0.21, lolita 0.20

### centroid+prompt
most over-represented nodes per race group (ratio to pooled):
- East Asian: e-boy x7.0, nautical x7.0, gyaru x5.1, kawaii x4.7, wonyoungism x4.1
- Indian: ancient-egypt x2.3, gangsta-rap x1.6, coconut-girl x1.3, bling-era x1.3, webcore x1.1
- Black: live-laugh-love x7.0, afrofuturism x4.7, bling-era x3.8, y2k-futurism x3.5, gangsta-rap x2.9
- White: decora x7.0, country x7.0, old-hollywood x7.0, pirate x7.0, western x7.0
- Middle Eastern: rave x7.0, that-girl x7.0, dandy x4.7, greaser x3.9, neko x3.5
- Latino Hispanic: glam-rock x7.0, vampire x3.5, femboy x2.3, femme-fatale x2.3, brazilian-bombshell x1.8
- Southeast Asian: biker x7.0, cybercore x7.0, y2k-futurism x3.5, dandy x2.3, wonyoungism x2.3

nodes loading most on race directions: wonyoungism 0.26, femboy 0.22, jirai-kei 0.20, babycore 0.20, kawaii 0.20, gyaru 0.20, emo 0.19, heisei-retro 0.19, afrofuturism 0.19, neko 0.18

### centroid+leace
most over-represented nodes per race group (ratio to pooled):
- East Asian: diner x7.0, kawaii x7.0, visual-kei x7.0, wonyoungism x7.0, babycore x4.0
- Indian: country x7.0, cybercore x3.5, nerd x3.5, live-laugh-love x2.3, scene x1.8
- Black: tropical x7.0, nerd x3.5, yuppie x2.4, brutalism x2.3, live-laugh-love x2.3
- White: afrofuturism x7.0, decora x7.0, femboy x7.0, old-hollywood x7.0, scene x5.2
- Middle Eastern: pirate x7.0, rave x7.0, nautical x7.0, neko x7.0, new-wave x7.0
- Latino Hispanic: burlesque x7.0, e-boy x7.0, surfer x7.0, femme-fatale x3.5, high-school-dream x3.5
- Southeast Asian: biker x7.0, cholo x2.0, emo-rap x1.8, emo x1.7, kidcore x1.6

nodes loading most on race directions: scene 0.24, metalhead 0.24, 2014-girly 0.23, scenecore 0.22, nu-metal 0.21, funk 0.21, hypebeast 0.21, hip-hop 0.21, cybercore 0.21, punk 0.21

### centroid+mask
most over-represented nodes per race group (ratio to pooled):
- East Asian: vectorheart x7.0, curly-girly x7.0, minimalism x3.5, vanilla-girl x2.1, gen-x-soft-club x1.2
- Indian: mid-century-modern x3.5, minimalism x3.5, pop-art x1.8, zen-x x1.7, mcbling x1.6
- Black: hands-up x7.0, meme-rap x7.0, glitch-art x1.4, gen-x-soft-club x1.2, analog-horror x1.1
- White: arts-and-crafts x7.0, dark-aero x7.0, beatnik x7.0, mid-century-modern x3.5, gen-x-soft-club x2.3
- Middle Eastern: film-noir x7.0, pop-art x3.5, zen-x x3.0, vanilla-girl x1.4, glitch-art x1.4
- Latino Hispanic: japandi x2.5, naturecore x2.0, mcbling x1.9, deep-fried-meme x1.1, fjortis x0.9
- Southeast Asian: mafia-aesthetic x7.0, medicalcore x7.0, hippie x7.0, electronic-body-music x7.0, dorfic x7.0

nodes loading most on race directions: devilcore 0.37, funfair-kitsch 0.35, lovecore 0.35, wacky-pomo 0.34, kidcore 0.32, horrorcore 0.32, memphis-jr 0.31, nostalgiacore 0.31, gothic 0.30, burlesque 0.30

### centroid+mask+leace
most over-represented nodes per race group (ratio to pooled):
- East Asian: babygirl x7.0, tomato-girl-summer x7.0, shamate x7.0, vectorheart x7.0, mafia-aesthetic x3.5
- Indian: minimalism x7.0, fairycore x3.5, old-web x2.3, japandi x1.8, dandy x1.6
- Black: pop-art x7.0, meme-rap x7.0, krushclub x7.0, beatnik x3.5, international-typographic-style x2.7
- White: western x7.0, hygge x3.5, dark-aero x3.5, dorfic x3.5, clean-girl x2.3
- Middle Eastern: arts-and-crafts x7.0, liminal-space x7.0, webcore x7.0, hygge x3.5, mafia-aesthetic x3.5
- Latino Hispanic: fairycore x3.5, japandi x3.5, clean-girl x2.3, vanilla-girl x1.1, fjortis x1.1
- Southeast Asian: rustic x7.0, medicalcore x7.0, glam-rock x7.0, coastal-grandmother x7.0, dorfic x3.5

nodes loading most on race directions: devilcore 0.40, decora 0.37, mlg 0.34, clowncore 0.34, digital-horror 0.33, funfair-kitsch 0.33, lovecore 0.33, nostalgiacore 0.33, meme-rap 0.32, babygirl 0.32

### head
most over-represented nodes per race group (ratio to pooled):
- East Asian: kawaii x7.0, soft-boy x5.6, gyaru x4.8, fairycore x4.7, heisei-retro x4.4
- Indian: film-noir x7.0, maid x7.0, goth x3.5, cybercore x3.5, bimbocore x3.3
- Black: afrofuturism x5.4, gangsta-rap x4.7, mcbling x4.7, coastal-grandmother x4.0, goth x3.5
- White: fairy-grunge x7.0, e-boy x7.0, 50s-suburbia x5.2, britpop x4.8, coconut-girl x3.5
- Middle Eastern: strega x4.9, hipster x4.0, riot-grrrl x3.5, cybercore x3.5, suburban-gothic x3.5
- Latino Hispanic: ethereal x7.0, new-romantic x7.0, twee x7.0, old-hollywood x3.5, fairycore x2.3
- Southeast Asian: indie-kid x7.0, hypebeast x3.5, wonyoungism x2.9, gyaru x2.2, heisei-retro x2.2

nodes loading most on race directions: wonyoungism 0.31, gyaru 0.24, babycore 0.24, femboy 0.24, heisei-retro 0.24, jirai-kei 0.23, kawaii 0.22, neko 0.21, gangsta-rap 0.21, lolita 0.20

### head_rw
most over-represented nodes per race group (ratio to pooled):
- East Asian: femboy x7.0, grunge x7.0, soft-boy x5.6, heisei-retro x5.5, gyaru x5.1
- Indian: maid x7.0, goth x7.0, cybercore x3.5, bimbocore x2.9, hippie x2.6
- Black: coastal-grandmother x6.0, afrofuturism x4.8, mcbling x4.7, gangsta-rap x4.5, baddie x2.8
- White: e-boy x7.0, fairy-grunge x7.0, 50s-suburbia x5.2, britpop x4.8, new-wave x3.5
- Middle Eastern: cybercore x3.5, riot-grrrl x3.5, strega x3.5, greaser x3.0, hair-metal x2.8
- Latino Hispanic: americana x7.0, new-romantic x7.0, twee x7.0, bling-era x2.5, indie-kid x2.3
- Southeast Asian: rave x7.0, indie-kid x4.7, wonyoungism x3.7, hypebeast x3.5, kawaii x3.5

nodes loading most on race directions: wonyoungism 0.31, gyaru 0.24, babycore 0.24, femboy 0.24, heisei-retro 0.24, jirai-kei 0.23, kawaii 0.22, neko 0.21, gangsta-rap 0.21, lolita 0.20

### head_rw+leace
most over-represented nodes per race group (ratio to pooled):
- East Asian: ethereal x7.0, gyaru x3.9, goth x3.5, fairycore x3.5, kawaii x3.5
- Indian: mod x7.0, regency x7.0, hippie x7.0, clean-girl x3.5, fairycore x3.5
- Black: femboy x7.0, indie-sleaze x7.0, new-money x4.7, cybercore x2.3, webcore x2.3
- White: e-boy x7.0, cybergoth x7.0, mob-wife x7.0, pirate x7.0, coconut-girl x3.5
- Middle Eastern: americana x7.0, baddie x3.5, new-romantic x3.5, beatnik x2.8, cybercore x2.3
- Latino Hispanic: soft-boy x7.0, glam-rock x3.5, kidcore x3.5, new-romantic x3.5, high-school-dream x3.5
- Southeast Asian: biker x7.0, indie-kid x7.0, rave x7.0, wonyoungism x3.5, kidcore x3.5

nodes loading most on race directions: scene 0.24, metalhead 0.24, 2014-girly 0.23, scenecore 0.22, nu-metal 0.21, funk 0.21, hypebeast 0.21, hip-hop 0.21, cybercore 0.21, punk 0.21

### head_rw+mask+leace
most over-represented nodes per race group (ratio to pooled):
- East Asian: vanilla-girl x3.5, mafia-aesthetic x3.5, electroclash x3.5, dollcore x2.3, waif x2.3
- Indian: new-wave x7.0, devilcore x7.0, vanilla-girl x3.5, dollcore x2.3, mcbling x2.0
- Black: glitch-art x7.0, goblincore x7.0, electroclash x3.5, krushclub x1.8, fjortis x1.8
- White: digital-horror x4.7, medicalcore x2.8, fjortis x1.8, e-girl x1.4, krushclub x1.3
- Middle Eastern: brazilian-bombshell x7.0, waif x4.7, dollcore x2.3, britpop x1.8, analog-horror x1.7
- Latino Hispanic: fairycore x7.0, curly-girly x7.0, digital-horror x2.3, bling-era x1.9, britpop x1.8
- Southeast Asian: zen-x x7.0, neofolk x7.0, afrofuturism x7.0, dorfic x7.0, mcbling x2.0

nodes loading most on race directions: devilcore 0.40, decora 0.37, mlg 0.34, clowncore 0.34, digital-horror 0.33, funfair-kitsch 0.33, lovecore 0.33, nostalgiacore 0.33, meme-rap 0.32, babygirl 0.32

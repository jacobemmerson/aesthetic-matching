Parity is measured on the probe half LEACE was not fitted on. Shuffled-label floor for this probe size: race TVD 0.230, gender TVD 0.106.

| config | race TVD | gender TVD | race acc (chance 0.143) | gender acc (chance 0.5) | LOO top1 | LOO top5 |
|---|---|---|---|---|---|---|
| centroid | 0.685 | 0.383 | 0.619 | 0.936 | 0.537 | 0.825 |
| centroid+prompt | 0.610 | 0.201 | 0.609 | 0.926 | 0.539 | 0.825 |
| centroid+leace | 0.270 | 0.131 | 0.285 | 0.625 | 0.527 | 0.826 |
| centroid+mask | 0.165 | 0.057 | 0.172 | 0.510 | 0.411 | 0.669 |
| centroid+mask+leace | 0.185 | 0.087 | 0.146 | 0.502 | 0.368 | 0.613 |
| head | 0.595 | 0.494 | 0.619 | 0.936 | 0.543 | 0.827 |
| head_rw | 0.615 | 0.500 | 0.619 | 0.936 | 0.539 | 0.828 |
| head_rw+leace | 0.290 | 0.171 | 0.285 | 0.625 | 0.528 | 0.822 |
| head_rw+mask+leace | 0.180 | 0.031 | 0.146 | 0.502 | 0.394 | 0.675 |

### centroid
most over-represented nodes per race group (ratio to pooled):
- East Asian: gorpcore x7.0, tiki x7.0, wonyoungism x5.0, kawaii x4.2, gyaru x4.1
- Indian: baddie x3.5, ancient-egypt x2.7, emo-rap x1.7, liminal-space x1.5, hip-hop x1.3
- Black: yuppie x4.1, hip-hop x3.3, mcbling x2.9, coconut-girl x2.4, southern-gothic x2.3
- White: country x7.0, decora x7.0, funk x7.0, pirate x7.0, old-hollywood x7.0
- Middle Eastern: diner x7.0, clean-girl x3.5, femboy x3.5, beatnik x2.4, greaser x2.2
- Latino Hispanic: glam-rock x7.0, hippie x7.0, flapper x7.0, coastal-grandmother x3.5, nu-metal x2.5
- Southeast Asian: biker x7.0, cybercore x7.0, rave x7.0, clean-girl x3.5, y2k-futurism x3.5

nodes loading most on race directions: wonyoungism 0.31, gyaru 0.24, femboy 0.24, jirai-kei 0.23, kawaii 0.22, lolita 0.20, decora 0.19, emo 0.19, otaku 0.18, scene 0.17

### centroid+prompt
most over-represented nodes per race group (ratio to pooled):
- East Asian: skater x4.7, kawaii x4.4, kidcore x4.2, wonyoungism x3.7, gyaru x3.5
- Indian: techwear x7.0, ancient-egypt x2.2, southern-gothic x1.8, emo-rap x1.2, webcore x1.1
- Black: yuppie x3.6, western x3.5, hip-hop x3.1, mcbling x2.5, dandy x2.3
- White: country x7.0, decora x7.0, old-hollywood x7.0, pirate x7.0, scene x7.0
- Middle Eastern: vanilla-girl x7.0, rave x7.0, that-girl x7.0, dandy x4.7, diner x3.5
- Latino Hispanic: coastal-grandmother x7.0, glam-rock x7.0, gorpcore x3.5, vampire x2.3, skater x2.3
- Southeast Asian: biker x7.0, cybercore x7.0, e-boy x3.5, clean-girl x2.3, wonyoungism x2.2

nodes loading most on race directions: wonyoungism 0.26, femboy 0.22, jirai-kei 0.20, kawaii 0.20, gyaru 0.20, emo 0.19, decora 0.18, scene 0.18, otaku 0.18, hipster 0.17

### centroid+leace
most over-represented nodes per race group (ratio to pooled):
- East Asian: diner x7.0, kawaii x7.0, kidcore x4.2, e-boy x3.5, 50s-suburbia x2.5
- Indian: fairycore x7.0, nerd x3.5, rave x3.5, emo-rap x2.4, surfer x2.3
- Black: hip-hop x7.0, new-romantic x7.0, tropical x7.0, nerd x3.5, yuppie x2.0
- White: country x7.0, decora x7.0, femboy x7.0, power-dressing x7.0, old-hollywood x7.0
- Middle Eastern: techwear x7.0, that-girl x7.0, wonyoungism x7.0, new-wave x7.0, dandy x4.7
- Latino Hispanic: gorpcore x7.0, e-boy x3.5, glam-rock x3.5, nautical x3.5, pirate x2.3
- Southeast Asian: biker x7.0, cybercore x1.8, emo x1.6, nu-metal x1.6, swag x1.4

nodes loading most on race directions: scene 0.24, metalhead 0.24, 2014-girly 0.23, nu-metal 0.21, funk 0.21, hypebeast 0.21, hip-hop 0.21, cybercore 0.21, punk 0.21, emo-rap 0.20

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
- East Asian: indie x7.0, femboy x7.0, scene x7.0, soft-girl x7.0, fairycore x4.7
- Indian: regency x7.0, swag x7.0, glam-rock x5.2, ethereal x3.5, goth x3.5
- Black: southern-gothic x7.0, tropical x7.0, coastal-grandmother x4.5, mcbling x4.1, goth x3.5
- White: e-boy x7.0, britpop x4.3, vampire x3.5, pirate x3.5, femme-fatale x2.6
- Middle Eastern: pirate x3.5, strega x2.7, hipster x2.7, greaser x2.4, beatnik x2.1
- Latino Hispanic: new-romantic x7.0, old-hollywood x4.7, americana x3.5, ethereal x3.5, twee x2.8
- Southeast Asian: biker x7.0, indie-kid x7.0, otaku x7.0, hypebeast x3.9, kidcore x3.5

nodes loading most on race directions: wonyoungism 0.31, gyaru 0.24, femboy 0.24, jirai-kei 0.23, kawaii 0.22, lolita 0.20, decora 0.19, emo 0.19, otaku 0.18, scene 0.17

### head_rw
most over-represented nodes per race group (ratio to pooled):
- East Asian: indie x7.0, femboy x7.0, scene x7.0, fairycore x5.2, webcore x4.4
- Indian: swag x7.0, rave x7.0, regency x7.0, glam-rock x5.2, maid x3.5
- Black: tropical x7.0, coastal-grandmother x4.1, mcbling x3.8, goth x3.5, hip-hop x2.7
- White: e-boy x7.0, metalhead x7.0, britpop x4.3, pirate x3.5, femme-fatale x3.5
- Middle Eastern: cybercore x3.5, pirate x3.5, hipster x3.5, strega x3.3, femme-fatale x2.3
- Latino Hispanic: gorpcore x7.0, new-romantic x7.0, old-hollywood x3.5, americana x3.2, hair-metal x3.0
- Southeast Asian: biker x7.0, edwardian x7.0, kidcore x7.0, indie-kid x7.0, otaku x7.0

nodes loading most on race directions: wonyoungism 0.31, gyaru 0.24, femboy 0.24, jirai-kei 0.23, kawaii 0.22, lolita 0.20, decora 0.19, emo 0.19, otaku 0.18, scene 0.17

### head_rw+leace
most over-represented nodes per race group (ratio to pooled):
- East Asian: ethereal x7.0, femboy x7.0, gyaru x3.9, goth x3.5, webcore x2.8
- Indian: hippie x7.0, glam-rock x5.2, cybercore x3.5, clean-girl x2.3, fairycore x2.3
- Black: webcore x2.8, hip-hop x2.7, mcbling x2.0, dandy x1.6, coastal-grandmother x1.4
- White: pirate x4.7, britpop x2.9, coconut-girl x2.8, swag x2.6, goth x2.3
- Middle Eastern: americana x7.0, new-romantic x7.0, cybercore x3.5, hipster x3.5, pirate x2.3
- Latino Hispanic: gorpcore x7.0, femme-fatale x3.1, hip-hop x2.7, clean-girl x2.3, emo-rap x2.3
- Southeast Asian: kidcore x7.0, maid x7.0, indie-kid x7.0, wonyoungism x2.7, rave x2.3

nodes loading most on race directions: scene 0.24, metalhead 0.24, 2014-girly 0.23, nu-metal 0.21, funk 0.21, hypebeast 0.21, hip-hop 0.21, cybercore 0.21, punk 0.21, emo-rap 0.20

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

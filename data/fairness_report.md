Parity is measured on the probe half LEACE was not fitted on. Shuffled-label floor for this probe size: race TVD 0.275, gender TVD 0.117.

| config | race TVD | gender TVD | race acc (chance 0.143) | gender acc (chance 0.5) | LOO top1 | LOO top5 |
|---|---|---|---|---|---|---|
| centroid | 0.825 | 0.479 | 0.619 | 0.936 | 0.451 | 0.724 |
| centroid+prompt | 0.800 | 0.324 | 0.609 | 0.926 | 0.445 | 0.719 |
| centroid+leace | 0.320 | 0.187 | 0.285 | 0.625 | 0.438 | 0.714 |
| centroid+mask | 0.165 | 0.057 | 0.172 | 0.510 | 0.411 | 0.669 |
| centroid+mask+leace | 0.185 | 0.087 | 0.146 | 0.502 | 0.368 | 0.613 |
| head | 0.665 | 0.494 | 0.619 | 0.936 | 0.442 | 0.725 |
| head_rw | 0.580 | 0.483 | 0.619 | 0.936 | 0.442 | 0.723 |
| head_rw+leace | 0.310 | 0.164 | 0.285 | 0.625 | 0.434 | 0.711 |
| head_rw+mask+leace | 0.180 | 0.031 | 0.146 | 0.502 | 0.394 | 0.675 |

### centroid
most over-represented nodes per race group (ratio to pooled):
- East Asian: wonyoungism x7.0, guochao x7.0, frutiger-eco x7.0, gyaru x5.6, gen-x-soft-club x5.2
- Indian: moe x4.2, reggae x3.5, brutalism x3.5, casino x3.5, afrofuturism x2.6
- Black: rude-boy x7.0, mcbling x4.7, bling-era x4.7, afrofuturism x4.4, gangsta-rap x4.3
- White: 50s-suburbia x7.0, raggare x7.0, peacock-revolution x7.0, gutter-punk x7.0, electronic-body-music x7.0
- Middle Eastern: tecktonik x7.0, nerd x7.0, film-noir x7.0, doomer x7.0, dandy x4.7
- Latino Hispanic: suburban-gothic x7.0, tomato-girl-summer x7.0, after-hours x7.0, glam-rock x7.0, femme-fatale x3.5
- Southeast Asian: sadboi x7.0, cleancore x7.0, krushclub x3.5, jejemon x2.4, babygirl x1.8

nodes loading most on race directions: wonyoungism 0.31, neo-chinese-style 0.28, guochao 0.27, larme-kei 0.27, nanchatte-seifuku 0.26, too-cool 0.26, shamate 0.26, sanriocore 0.26, himekaji 0.25, gyaru 0.24

### centroid+prompt
most over-represented nodes per race group (ratio to pooled):
- East Asian: wonyoungism x7.0, shamate x7.0, gyaru x7.0, emo-rap x7.0, babygirl x4.4
- Indian: reggae x3.5, brutalism x3.5, zen-x x2.6, cholo x2.5, moe x2.3
- Black: tropical x7.0, rude-boy x7.0, afrofuturism x7.0, yuppie x5.6, mcbling x4.7
- White: pirate x7.0, gutter-punk x7.0, neofolk x7.0, old-hollywood x7.0, decora x7.0
- Middle Eastern: pop-art x7.0, ocean-grunge x7.0, greaser x7.0, dandy x7.0, curly-girly x7.0
- Latino Hispanic: weimar-cabaret x7.0, deathrock x4.7, nazi-chic x4.0, tecktonik x3.5, femme-fatale x3.5
- Southeast Asian: sadboi x7.0, peacock-revolution x7.0, krushclub x7.0, raggare x3.5, jejemon x2.0

nodes loading most on race directions: wonyoungism 0.26, shamate 0.23, weeaboo 0.23, femboy 0.22, gopnik 0.22, sanriocore 0.22, femcel-anime-subculture 0.22, too-cool 0.21, nanchatte-seifuku 0.21, fairy-kei 0.21

### centroid+leace
most over-represented nodes per race group (ratio to pooled):
- East Asian: gabber x7.0, glitch-art x7.0, guochao x7.0, gyaru x7.0, emo-rap x7.0
- Indian: yugo-nostalgia x7.0, partille-johnny x7.0, nerd x7.0, liminal-space x7.0, country x7.0
- Black: 50s-suburbia x7.0, tropical x7.0, skinhead x4.7, yuppie x4.2, lad-culture x3.5
- White: slavic-winter x7.0, old-hollywood x7.0, net-art x7.0, peacock-revolution x7.0, decora x7.0
- Middle Eastern: rave x7.0, pop-art x7.0, ocean-grunge x7.0, dandy x7.0, emo x7.0
- Latino Hispanic: surrealism x7.0, tecktonik x7.0, burlesque x7.0, deathrock x4.7, casino x4.7
- Southeast Asian: babygirl x3.5, raggare x3.5, naturecore x3.5, deep-fried-meme x2.8, krushclub x2.3

nodes loading most on race directions: gopnik 0.29, nazi-chic 0.27, tecktonik 0.26, gutter-punk 0.25, raggare 0.25, scene 0.24, metalhead 0.24, trap-metal 0.24, shamate 0.24, electroclash 0.24

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
- East Asian: gyaru x7.0, emo-rap x7.0, weeaboo x7.0, medicalcore x3.5, coconut-girl x3.5
- Indian: corporate-grunge x7.0, bling-era x7.0, hands-up x5.2, that-girl x4.7, new-beat x3.0
- Black: dandy x7.0, reggae x5.2, afrofuturism x5.0, gangsta-rap x4.8, yuppie x4.7
- White: knightcore x7.0, e-boy x7.0, hair-metal x7.0, high-school-dream x7.0, femme-fatale x7.0
- Middle Eastern: tecktonik x7.0, sadboi x7.0, doomer x7.0, greaser x7.0, guido x5.2
- Latino Hispanic: recession-pop x7.0, new-romantic x7.0, choni x7.0, old-hollywood x4.7, gutter-punk x3.5
- Southeast Asian: krushclub x4.7, shamate x4.3, jejemon x3.2, too-cool x2.4, babygirl x1.4

nodes loading most on race directions: wonyoungism 0.31, neo-chinese-style 0.28, guochao 0.27, larme-kei 0.27, nanchatte-seifuku 0.26, too-cool 0.26, shamate 0.26, sanriocore 0.26, himekaji 0.25, gyaru 0.24

### head_rw
most over-represented nodes per race group (ratio to pooled):
- East Asian: gurokawa x7.0, gyaru x7.0, emo-rap x7.0, shamate x4.2, hands-up x3.5
- Indian: tomato-girl-summer x7.0, nerdcore x7.0, hippie x7.0, bling-era x7.0, corporate-grunge x7.0
- Black: afrofuturism x7.0, dandy x7.0, gangsta-rap x5.7, reggae x5.6, meme-rap x3.5
- White: slavic-doll x7.0, beatnik x7.0, knightcore x7.0, old-hollywood x7.0, gabber x7.0
- Middle Eastern: doomer x7.0, black-metal x5.2, skinhead x3.5, analog-horror x3.5, partille-johnny x2.4
- Latino Hispanic: recession-pop x7.0, new-romantic x7.0, horrorcore x7.0, bimbocore x7.0, gutter-punk x3.5
- Southeast Asian: krushclub x4.7, weeaboo x3.8, jejemon x3.1, shamate x2.8, too-cool x2.5

nodes loading most on race directions: wonyoungism 0.31, neo-chinese-style 0.28, guochao 0.27, larme-kei 0.27, nanchatte-seifuku 0.26, too-cool 0.26, shamate 0.26, sanriocore 0.26, himekaji 0.25, gyaru 0.24

### head_rw+leace
most over-represented nodes per race group (ratio to pooled):
- East Asian: nerdcore x7.0, hands-up x7.0, emo-rap x7.0, new-beat x3.5, dandy x3.5
- Indian: reggae x3.5, new-beat x3.5, haunted-mound x3.5, dandy x3.5, yuppie x2.8
- Black: urbancore x7.0, gen-x-soft-club x7.0, cholo x7.0, reggae x3.5, gangsta-rap x3.5
- White: wonyoungism x7.0, sadboi x7.0, knightcore x7.0, horrorcore x7.0, femme-fatale x7.0
- Middle Eastern: baddie x7.0, skinhead x7.0, devilcore x7.0, doomer x7.0, black-metal x4.2
- Latino Hispanic: recession-pop x7.0, net-art x7.0, keller-synth x7.0, cleancore x7.0, greaser x3.5
- Southeast Asian: shamate x7.0, heroin-chic x7.0, gopnik x7.0, clovercore x7.0, yugo-nostalgia x3.5

nodes loading most on race directions: gopnik 0.29, nazi-chic 0.27, tecktonik 0.26, gutter-punk 0.25, raggare 0.25, scene 0.24, metalhead 0.24, trap-metal 0.24, shamate 0.24, electroclash 0.24

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

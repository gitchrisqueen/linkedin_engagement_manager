#  Copyright (c) 2024. Christopher Queen Consulting LLC (http://www.ChristopherQueenConsulting.com/)
import os
import tempfile
import zipfile
from random import randint
from typing import Tuple, Any

import streamlit as st
import streamlit_ext as ste
from markdownify import markdownify as md
from openai import OpenAI
from streamlit.runtime.uploaded_file_manager import UploadedFile

CODE_LANGUAGES = [
    "abap", "abnf", "actionscript", "ada", "agda", "al", "antlr4", "apacheconf",
    "apex", "apl", "applescript", "aql", "arduino", "arff", "asciidoc", "asm6502",
    "asmatmel", "aspnet", "autohotkey", "autoit", "avisynth", "avroIdl", "bash",
    "basic", "batch", "bbcode", "bicep", "birb", "bison", "bnf", "brainfuck",
    "brightscript", "bro", "bsl", "c", "cfscript", "chaiscript", "cil", "clike",
    "clojure", "cmake", "cobol", "coffeescript", "concurnas", "coq", "cpp", "crystal",
    "csharp", "cshtml", "csp", "cssExtras", "css", "csv", "cypher", "d", "dart",
    "dataweave", "dax", "dhall", "diff", "django", "dnsZoneFile", "docker", "dot",
    "ebnf", "editorconfig", "eiffel", "ejs", "elixir", "elm", "erb", "erlang",
    "etlua", "excelFormula", "factor", "falselang", "firestoreSecurityRules", "flow",
    "fortran", "fsharp", "ftl", "gap", "gcode", "gdscript", "gedcom", "gherkin",
    "git", "glsl", "gml", "gn", "goModule", "go", "graphql", "groovy", "haml",
    "handlebars", "haskell", "haxe", "hcl", "hlsl", "hoon", "hpkp", "hsts", "http",
    "ichigojam", "icon", "icuMessageFormat", "idris", "iecst", "ignore", "inform7",
    "ini", "io", "j", "java", "javadoc", "javadoclike", "javascript", "javastacktrace",
    "jexl", "jolie", "jq", "jsExtras", "jsTemplates", "jsdoc", "json", "json5", "jsonp",
    "jsstacktrace", "jsx", "julia", "keepalived", "keyman", "kotlin", "kumir", "kusto",
    "latex", "latte", "less", "lilypond", "liquid", "lisp", "livescript", "llvm", "log",
    "lolcode", "lua", "magma", "makefile", "markdown", "markupTemplating", "markup",
    "matlab", "maxscript", "mel", "mermaid", "mizar", "mongodb", "monkey", "moonscript",
    "n1ql", "n4js", "nand2tetrisHdl", "naniscript", "nasm", "neon", "nevod", "nginx",
    "nim", "nix", "nsis", "objectivec", "ocaml", "opencl", "openqasm", "oz", "parigp",
    "parser", "pascal", "pascaligo", "pcaxis", "peoplecode", "perl", "phpExtras", "php",
    "phpdoc", "plsql", "powerquery", "powershell", "processing", "prolog", "promql",
    "properties", "protobuf", "psl", "pug", "puppet", "pure", "purebasic", "purescript",
    "python", "q", "qml", "qore", "qsharp", "r", "racket", "reason", "regex", "rego",
    "renpy", "rest", "rip", "roboconf", "robotframework", "ruby", "rust", "sas", "sass",
    "scala", "scheme", "scss", "shellSession", "smali", "smalltalk", "smarty", "sml",
    "solidity", "solutionFile", "soy", "sparql", "splunkSpl", "sqf", "sql", "squirrel",
    "stan", "stylus", "swift", "systemd", "t4Cs", "t4Templating", "t4Vb", "tap", "tcl",
    "textile", "toml", "tremor", "tsx", "tt2", "turtle", "twig", "typescript", "typoscript",
    "unrealscript", "uorazor", "uri", "v", "vala", "vbnet", "velocity", "verilog", "vhdl",
    "vim", "visualBasic", "warpscript", "wasm", "webIdl", "wiki", "wolfram", "wren", "xeora",
    "xmlDoc", "xojo", "xquery", "yaml", "yang", "zig"
]

mime_types_str = """
.3dm	x-world/x-3dmf
.3dmf	x-world/x-3dmf
.7z	application/x-7z-compressed
.a	application/octet-stream
.aab	application/x-authorware-bin
.aam	application/x-authorware-map
.aas	application/x-authorware-seg
.abc	text/vnd.abc
.acgi	text/html
.afl	video/animaflex
.ai	application/postscript
.aif	audio/aiff
.aif	audio/x-aiff
.aifc	audio/aiff
.aifc	audio/x-aiff
.aiff	audio/aiff
.aiff	audio/x-aiff
.aim	application/x-aim
.aip	text/x-audiosoft-intra
.ani	application/x-navi-animation
.aos	application/x-nokia-9000-communicator-add-on-software
.aps	application/mime
.arc	application/octet-stream
.arj	application/arj
.arj	application/octet-stream
.art	image/x-jg
.asf	video/x-ms-asf
.asm	text/x-asm
.asp	text/asp
.asx	application/x-mplayer2
.asx	video/x-ms-asf
.asx	video/x-ms-asf-plugin
.au	audio/basic
.au	audio/x-au
.avi	application/x-troff-msvideo
.avi	video/avi
.avi	video/msvideo
.avi	video/x-msvideo
.avs	video/avs-video
.bcpio	application/x-bcpio
.bin	application/mac-binary
.bin	application/macbinary
.bin	application/octet-stream
.bin	application/x-binary
.bin	application/x-macbinary
.bm	image/bmp
.bmp	image/bmp
.bmp	image/x-windows-bmp
.boo	application/book
.book	application/book
.boz	application/x-bzip2
.bsh	application/x-bsh
.bz	application/x-bzip
.bz2	application/x-bzip2
.c	text/plain
.c	text/x-c
.c++	text/plain
.cat	application/vnd.ms-pki.seccat
.cc	text/plain
.cc	text/x-c
.ccad	application/clariscad
.cco	application/x-cocoa
.cdf	application/cdf
.cdf	application/x-cdf
.cdf	application/x-netcdf
.cer	application/pkix-cert
.cer	application/x-x509-ca-cert
.cha	application/x-chat
.chat	application/x-chat
.class	application/java
.class	application/java-byte-code
.class	application/x-java-class
.com	application/octet-stream
.com	text/plain
.conf	text/plain
.cpio	application/x-cpio
.cpp	text/x-c
.cpt	application/mac-compactpro
.cpt	application/x-compactpro
.cpt	application/x-cpt
.crl	application/pkcs-crl
.crl	application/pkix-crl
.crt	application/pkix-cert
.crt	application/x-x509-ca-cert
.crt	application/x-x509-user-cert
.csh	application/x-csh
.csh	text/x-script.csh
.css	application/x-pointplus
.css	text/css
.csv	text/csv
.cxx	text/plain
.dcr	application/x-director
.deepv	application/x-deepv
.def	text/plain
.der	application/x-x509-ca-cert
.dif	video/x-dv
.dir	application/x-director
.dl	video/dl
.dl	video/x-dl
.doc	application/msword
.docx	application/vnd.openxmlformats-officedocument.wordprocessingml.document
.dot	application/msword
.dp	application/commonground
.drw	application/drafting
.dump	application/octet-stream
.dv	video/x-dv
.dvi	application/x-dvi
.dwf	model/vnd.dwf
.dwg	application/acad
.dwg	image/vnd.dwg
.dwg	image/x-dwg
.dxf	application/dxf
.dxf	image/vnd.dwg
.dxf	image/x-dwg
.dxr	application/x-director
.el	text/x-script.elisp
.elc	application/x-elc
.env	application/x-envoy
.eot	application/vnd.ms-fontobject
.eps	application/postscript
.es	application/x-esrehber
.etx	text/x-setext
.evy	application/envoy
.evy	application/x-envoy
.exe	application/octet-stream
.f	text/plain
.f	text/x-fortran
.f77	text/x-fortran
.f90	text/plain
.f90	text/x-fortran
.fdf	application/vnd.fdf
.fif	application/fractals
.fif	image/fif
.flac	audio/flac
.fli	video/fli
.fli	video/x-fli
.flo	image/florian
.flx	text/vnd.fmi.flexstor
.fmf	video/x-atomic3d-feature
.for	text/plain
.for	text/x-fortran
.fpx	image/vnd.fpx
.fpx	image/vnd.net-fpx
.frl	application/freeloader
.funk	audio/make
.g	text/plain
.g3	image/g3fax
.gif	image/gif
.gl	video/gl
.gl	video/x-gl
.gsd	audio/x-gsm
.gsm	audio/x-gsm
.gsp	application/x-gsp
.gss	application/x-gss
.gtar	application/x-gtar
.gz	application/x-compressed
.gz	application/x-gzip
.gzip	application/x-gzip
.gzip	multipart/x-gzip
.h	text/plain
.h	text/x-h
.hdf	application/x-hdf
.help	application/x-helpfile
.hgl	application/vnd.hp-hpgl
.hh	text/plain
.hh	text/x-h
.hlb	text/x-script
.hlp	application/hlp
.hlp	application/x-helpfile
.hlp	application/x-winhelp
.hpg	application/vnd.hp-hpgl
.hpgl	application/vnd.hp-hpgl
.hqx	application/binhex
.hqx	application/binhex4
.hqx	application/mac-binhex
.hqx	application/mac-binhex40
.hqx	application/x-binhex40
.hqx	application/x-mac-binhex40
.hta	application/hta
.htc	text/x-component
.htm	text/html
.html	text/html
.htmls	text/html
.htt	text/webviewhtml
.htx	text/html
.ice	x-conference/x-cooltalk
.ico	image/x-icon
.ics	text/calendar
.idc	text/plain
.ief	image/ief
.iefs	image/ief
.iges	application/iges
.iges	model/iges
.igs	application/iges
.igs	model/iges
.ima	application/x-ima
.imap	application/x-httpd-imap
.inf	application/inf
.ins	application/x-internett-signup
.ip	application/x-ip2
.isu	video/x-isvideo
.it	audio/it
.iv	application/x-inventor
.ivr	i-world/i-vrml
.ivy	application/x-livescreen
.jam	audio/x-jam
.jav	text/plain
.jav	text/x-java-source
.java	text/plain
.java	text/x-java-source
.jcm	application/x-java-commerce
.jfif	image/jpeg
.jfif	image/pjpeg
.jfif-tbnl	image/jpeg
.jpe	image/jpeg
.jpe	image/pjpeg
.jpeg	image/jpeg
.jpeg	image/pjpeg
.jpg	image/jpeg
.jpg	image/pjpeg
.jps	image/x-jps
.js	application/x-javascript
.js	application/javascript
.js	application/ecmascript
.js	text/javascript
.js	text/ecmascript
.json	application/json
.jut	image/jutvision
.kar	audio/midi
.kar	music/x-karaoke
.ksh	application/x-ksh
.ksh	text/x-script.ksh
.la	audio/nspaudio
.la	audio/x-nspaudio
.lam	audio/x-liveaudio
.latex	application/x-latex
.lha	application/lha
.lha	application/octet-stream
.lha	application/x-lha
.lhx	application/octet-stream
.list	text/plain
.lma	audio/nspaudio
.lma	audio/x-nspaudio
.log	text/plain
.lsp	application/x-lisp
.lsp	text/x-script.lisp
.lst	text/plain
.lsx	text/x-la-asf
.ltx	application/x-latex
.lzh	application/octet-stream
.lzh	application/x-lzh
.lzx	application/lzx
.lzx	application/octet-stream
.lzx	application/x-lzx
.m	text/plain
.m	text/x-m
.m1v	video/mpeg
.m2a	audio/mpeg
.m2v	video/mpeg
.m3u	audio/x-mpequrl
.man	application/x-troff-man
.map	application/x-navimap
.mar	text/plain
.mbd	application/mbedlet
.mc$	application/x-magic-cap-package-1.0
.mcd	application/mcad
.mcd	application/x-mathcad
.mcf	image/vasa
.mcf	text/mcf
.mcp	application/netmc
.me	application/x-troff-me
.mht	message/rfc822
.mhtml	message/rfc822
.mid	application/x-midi
.mid	audio/midi
.mid	audio/x-mid
.mid	audio/x-midi
.mid	music/crescendo
.mid	x-music/x-midi
.midi	application/x-midi
.midi	audio/midi
.midi	audio/x-mid
.midi	audio/x-midi
.midi	music/crescendo
.midi	x-music/x-midi
.mif	application/x-frame
.mif	application/x-mif
.mime	message/rfc822
.mime	www/mime
.mjf	audio/x-vnd.audioexplosion.mjuicemediafile
.mjpg	video/x-motion-jpeg
.mka	audio/x-matroska
.mkv	video/x-matroska
.mm	application/base64
.mm	application/x-meme
.mme	application/base64
.mod	audio/mod
.mod	audio/x-mod
.moov	video/quicktime
.mov	video/quicktime
.movie	video/x-sgi-movie
.mp2	audio/mpeg
.mp2	audio/x-mpeg
.mp2	video/mpeg
.mp2	video/x-mpeg
.mp2	video/x-mpeq2a
.mp3	audio/mpeg3
.mp3	audio/x-mpeg-3
.mp3	video/mpeg
.mp3	video/x-mpeg
.mp4	video/mp4
.mpa	audio/mpeg
.mpa	video/mpeg
.mpc	application/x-project
.mpe	video/mpeg
.mpeg	video/mpeg
.mpg	audio/mpeg
.mpg	video/mpeg
.mpga	audio/mpeg
.mpp	application/vnd.ms-project
.mpt	application/x-project
.mpv	application/x-project
.mpx	application/x-project
.mrc	application/marc
.ms	application/x-troff-ms
.mv	video/x-sgi-movie
.my	audio/make
.mzz	application/x-vnd.audioexplosion.mzz
.nap	image/naplps
.naplps	image/naplps
.nc	application/x-netcdf
.ncm	application/vnd.nokia.configuration-message
.nif	image/x-niff
.niff	image/x-niff
.nix	application/x-mix-transfer
.nsc	application/x-conference
.nvd	application/x-navidoc
.o	application/octet-stream
.oda	application/oda
.ogg	audio/ogg
.ogg	video/ogg
.omc	application/x-omc
.omcd	application/x-omcdatamaker
.omcr	application/x-omcregerator
.otf	font/otf
.p	text/x-pascal
.p10	application/pkcs10
.p10	application/x-pkcs10
.p12	application/pkcs-12
.p12	application/x-pkcs12
.p7a	application/x-pkcs7-signature
.p7c	application/pkcs7-mime
.p7c	application/x-pkcs7-mime
.p7m	application/pkcs7-mime
.p7m	application/x-pkcs7-mime
.p7r	application/x-pkcs7-certreqresp
.p7s	application/pkcs7-signature
.part	application/pro_eng
.pas	text/pascal
.pbm	image/x-portable-bitmap
.pcl	application/vnd.hp-pcl
.pcl	application/x-pcl
.pct	image/x-pict
.pcx	image/x-pcx
.pdb	chemical/x-pdb
.pdf	application/pdf
.pfunk	audio/make
.pfunk	audio/make.my.funk
.pgm	image/x-portable-graymap
.pgm	image/x-portable-greymap
.pic	image/pict
.pict	image/pict
.pkg	application/x-newton-compatible-pkg
.pko	application/vnd.ms-pki.pko
.pl	text/plain
.pl	text/x-script.perl
.plx	application/x-pixclscript
.pm	image/x-xpixmap
.pm	text/x-script.perl-module
.pm4	application/x-pagemaker
.pm5	application/x-pagemaker
.png	image/png
.pnm	application/x-portable-anymap
.pnm	image/x-portable-anymap
.pot	application/mspowerpoint
.pot	application/vnd.ms-powerpoint
.pov	model/x-pov
.ppa	application/vnd.ms-powerpoint
.ppm	image/x-portable-pixmap
.pps	application/mspowerpoint
.pps	application/vnd.ms-powerpoint
.ppt	application/mspowerpoint
.ppt	application/powerpoint
.ppt	application/vnd.ms-powerpoint
.ppt	application/x-mspowerpoint
.pptx	application/vnd.openxmlformats-officedocument.presentationml.presentation
.ppz	application/mspowerpoint
.pre	application/x-freelance
.prt	application/pro_eng
.ps	application/postscript
.psd	application/octet-stream
.pvu	paleovu/x-pv
.pwz	application/vnd.ms-powerpoint
.py	text/x-script.phyton
.pyc	application/x-bytecode.python
.qcp	audio/vnd.qcelp
.qd3	x-world/x-3dmf
.qd3d	x-world/x-3dmf
.qif	image/x-quicktime
.qt	video/quicktime
.qtc	video/x-qtc
.qti	image/x-quicktime
.qtif	image/x-quicktime
.ra	audio/x-pn-realaudio
.ra	audio/x-pn-realaudio-plugin
.ra	audio/x-realaudio
.ram	audio/x-pn-realaudio
.ras	application/x-cmu-raster
.ras	image/cmu-raster
.ras	image/x-cmu-raster
.rast	image/cmu-raster
.rar	application/vnd.rar
.rexx	text/x-script.rexx
.rf	image/vnd.rn-realflash
.rgb	image/x-rgb
.rm	application/vnd.rn-realmedia
.rm	audio/x-pn-realaudio
.rmi	audio/mid
.rmm	audio/x-pn-realaudio
.rmp	audio/x-pn-realaudio
.rmp	audio/x-pn-realaudio-plugin
.rng	application/ringing-tones
.rng	application/vnd.nokia.ringing-tone
.rnx	application/vnd.rn-realplayer
.roff	application/x-troff
.rp	image/vnd.rn-realpix
.rpm	audio/x-pn-realaudio-plugin
.rt	text/richtext
.rt	text/vnd.rn-realtext
.rtf	application/rtf
.rtf	application/x-rtf
.rtf	text/richtext
.rtx	application/rtf
.rtx	text/richtext
.rv	video/vnd.rn-realvideo
.s	text/x-asm
.s3m	audio/s3m
.saveme	application/octet-stream
.sbk	application/x-tbook
.scm	application/x-lotusscreencam
.scm	text/x-script.guile
.scm	text/x-script.scheme
.scm	video/x-scm
.sdml	text/plain
.sdp	application/sdp
.sdp	application/x-sdp
.sdr	application/sounder
.sea	application/sea
.sea	application/x-sea
.set	application/set
.sgm	text/sgml
.sgm	text/x-sgml
.sgml	text/sgml
.sgml	text/x-sgml
.sh	application/x-bsh
.sh	application/x-sh
.sh	application/x-shar
.sh	text/x-script.sh
.shar	application/x-bsh
.shar	application/x-shar
.shtml	text/html
.shtml	text/x-server-parsed-html
.sid	audio/x-psid
.sit	application/x-sit
.sit	application/x-stuffit
.skd	application/x-koan
.skm	application/x-koan
.skp	application/x-koan
.skt	application/x-koan
.sl	application/x-seelogo
.smi	application/smil
.smil	application/smil
.snd	audio/basic
.snd	audio/x-adpcm
.sol	application/solids
.spc	application/x-pkcs7-certificates
.spc	text/x-speech
.spl	application/futuresplash
.spr	application/x-sprite
.sprite	application/x-sprite
.src	application/x-wais-source
.ssi	text/x-server-parsed-html
.ssm	application/streamingmedia
.sst	application/vnd.ms-pki.certstore
.step	application/step
.stl	application/sla
.stl	application/vnd.ms-pki.stl
.stl	application/x-navistyle
.stp	application/step
.sv4cpio	application/x-sv4cpio
.sv4crc	application/x-sv4crc
.svf	image/vnd.dwg
.svf	image/x-dwg
.svg	image/svg+xml
.svr	application/x-world
.svr	x-world/x-svr
.swf	application/x-shockwave-flash
.t	application/x-troff
.talk	text/x-speech
.tar	application/x-tar
.tbk	application/toolbook
.tbk	application/x-tbook
.tcl	application/x-tcl
.tcl	text/x-script.tcl
.tcsh	text/x-script.tcsh
.tex	application/x-tex
.texi	application/x-texinfo
.texinfo	application/x-texinfo
.text	application/plain
.text	text/plain
.tgz	application/gnutar
.tgz	application/x-compressed
.tif	image/tiff
.tif	image/x-tiff
.tiff	image/tiff
.tiff	image/x-tiff
.tr	application/x-troff
.ts	video/mp2t
.tsi	audio/tsp-audio
.tsp	application/dsptype
.tsp	audio/tsplayer
.tsv	text/tab-separated-values
.turbot	image/florian
.txt	text/plain
.uil	text/x-uil
.uni	text/uri-list
.unis	text/uri-list
.unv	application/i-deas
.uri	text/uri-list
.uris	text/uri-list
.ustar	application/x-ustar
.ustar	multipart/x-ustar
.uu	application/octet-stream
.uu	text/x-uuencode
.uue	text/x-uuencode
.vcd	application/x-cdlink
.vcs	text/x-vcalendar
.vda	application/vda
.vdo	video/vdo
.vew	application/groupwise
.viv	video/vivo
.viv	video/vnd.vivo
.vivo	video/vivo
.vivo	video/vnd.vivo
.vmd	application/vocaltec-media-desc
.vmf	application/vocaltec-media-file
.voc	audio/voc
.voc	audio/x-voc
.vos	video/vosaic
.vox	audio/voxware
.vqe	audio/x-twinvq-plugin
.vqf	audio/x-twinvq
.vql	audio/x-twinvq-plugin
.vrml	application/x-vrml
.vrml	model/vrml
.vrml	x-world/x-vrml
.vrt	x-world/x-vrt
.vsd	application/x-visio
.vst	application/x-visio
.vsw	application/x-visio
.w60	application/wordperfect6.0
.w61	application/wordperfect6.1
.w6w	application/msword
.wav	audio/wav
.wav	audio/x-wav
.wb1	application/x-qpro
.wbmp	image/vnd.wap.wbmp
.web	application/vnd.xara
.webm	video/webm
.webp	image/webp
.wiz	application/msword
.wk1	application/x-123
.wmf	windows/metafile
.wml	text/vnd.wap.wml
.wmlc	application/vnd.wap.wmlc
.wmls	text/vnd.wap.wmlscript
.wmlsc	application/vnd.wap.wmlscriptc
.word	application/msword
.woff	font/woff
.woff2	font/woff2
.wp	application/wordperfect
.wp5	application/wordperfect
.wp5	application/wordperfect6.0
.wp6	application/wordperfect
.wpd	application/wordperfect
.wpd	application/x-wpwin
.wq1	application/x-lotus
.wri	application/mswrite
.wri	application/x-wri
.wrl	application/x-world
.wrl	model/vrml
.wrl	x-world/x-vrml
.wrz	model/vrml
.wrz	x-world/x-vrml
.wsc	text/scriplet
.wsrc	application/x-wais-source
.wtk	application/x-wintalk
.xbm	image/x-xbitmap
.xbm	image/x-xbm
.xbm	image/xbm
.xdr	video/x-amt-demorun
.xgz	xgl/drawing
.xif	image/vnd.xiff
.xl     application/excel
.xla	application/excel
.xla	application/x-excel
.xla	application/x-msexcel
.xlb	application/excel
.xlb	application/vnd.ms-excel
.xlb	application/x-excel
.xlc	application/excel
.xlc	application/vnd.ms-excel
.xlc	application/x-excel
.xld	application/excel
.xld	application/x-excel
.xlk	application/excel
.xlk	application/x-excel
.xll	application/excel
.xll	application/vnd.ms-excel
.xll	application/x-excel
.xlm	application/excel
.xlm	application/vnd.ms-excel
.xlm	application/x-excel
.xls	application/excel
.xls	application/vnd.ms-excel
.xls	application/x-excel
.xls	application/x-msexcel
.xlt	application/excel
.xlt	application/x-excel
.xlv	application/excel
.xlv	application/x-excel
.xlw	application/excel
.xlw	application/vnd.ms-excel
.xlw	application/x-excel
.xlw	application/x-msexcel
.xm	audio/xm
.xml	application/xml
.xml	text/xml
.xmz	xgl/movie
.xpix	application/x-vnd.ls-xpix
.xpm	image/x-xpixmap
.xpm	image/xpm
.x-png	image/png
.xlsx	application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
.xsr	video/x-amt-showrun
.xwd	image/x-xwd
.xwd	image/x-xwindowdump
.xyz	chemical/x-pdb
.yaml	application/x-yaml
.yml	application/x-yaml
.z	application/x-compress
.z	application/x-compressed
.zip	application/x-compressed
.zip	application/x-zip-compressed
.zip	application/zip
.zip	multipart/x-zip
.zoo	application/octet-stream
.zsh	text/x-script.zsh
"""


@st.cache_data
def get_custom_css():
    # Embed custom fonts using HTML and CSS
    css = """
        <style>
            @font-face {
                font-family: "Franklin Gothic";
                src: url("https://db.onlinewebfonts.com/t/9c9dbb999dd7068f51335d93cc7328bd.eot");
                src: url("https://db.onlinewebfonts.com/t/9c9dbb999dd7068f51335d93cc7328bd.eot?#iefix")format("embedded-opentype"),
                url("https://db.onlinewebfonts.com/t/9c9dbb999dd7068f51335d93cc7328bd.woff2")format("woff2"),
                url("https://db.onlinewebfonts.com/t/9c9dbb999dd7068f51335d93cc7328bd.woff")format("woff"),
                url("https://db.onlinewebfonts.com/t/9c9dbb999dd7068f51335d93cc7328bd.ttf")format("truetype"),
                url("https://db.onlinewebfonts.com/t/9c9dbb999dd7068f51335d93cc7328bd.svg#Franklin Gothic")format("svg");
            }

            @font-face {
                font-family: 'ITC New Baskerville';
                src: url("https://db.onlinewebfonts.com/t/501ade6e29baa5c62c15ec28f3ed2c62.eot");
                src: url("https://db.onlinewebfonts.com/t/501ade6e29baa5c62c15ec28f3ed2c62.eot?#iefix")format("embedded-opentype"),
                url("https://db.onlinewebfonts.com/t/501ade6e29baa5c62c15ec28f3ed2c62.woff2")format("woff2"),
                url("https://db.onlinewebfonts.com/t/501ade6e29baa5c62c15ec28f3ed2c62.woff")format("woff"),
                url("https://db.onlinewebfonts.com/t/501ade6e29baa5c62c15ec28f3ed2c62.ttf")format("truetype"),
                url("https://db.onlinewebfonts.com/t/501ade6e29baa5c62c15ec28f3ed2c62.svg#ITC New Baskerville")format("svg");
            }

            body {
                font-family: 'Franklin Gothic', sans-serif;
            }

            h1, h2, h3, h4, h5, h6 {
                font-family: 'Franklin Gothic', sans-serif;
                font-weight: normal;
            }

            p {
                font-family: 'ITC New Baskerville', sans-serif;
                font-weight: normal;
            }
        </style>
        """
    return css


@st.cache_resource(hash_funcs={OpenAI: id})
def get_openai_client_instance(temperature: float, model: str) -> OpenAI:
    client = OpenAI(
        # This is the default and can be omitted
        # api_key=os.environ.get("OPENAI_API_KEY"),
    )

    """
    This function returns a cached instance of ChatOpenAI based on the temperature and model.
    If the temperature or model changes, a new instance will be created and cached.
    """
    return client


def get_file_extension_from_filepath(file_path: str, remove_leading_dot: bool = False) -> str:
    basename = os.path.basename(file_path)
    file_name, file_extension = os.path.splitext(basename)
    if remove_leading_dot and file_extension.startswith("."):
        # st.info("Removing leading dot from file extension: " + file_extension)
        file_extension = file_extension[1:]

    if file_extension:
        file_extension = file_extension.lower()

    # st.info("Base Name: " + basename + " | File Name: " + file_name + " | File Extension : " + file_extension)

    return file_extension


def get_language_from_file_path(file_path):
    # Extract file extension from the file path
    file_extension = get_file_extension_from_filepath(file_path, True)

    # Check if the file extension exists in the mapping
    if file_extension in CODE_LANGUAGES:
        # st.info(file_extension + " | Found in CODE_LANGUAGES")
        return file_extension
    else:
        # st.info(file_extension + " | NOT Found in CODE_LANGUAGES")
        return None  # Return None if the file extension is not found


def define_code_language_selection(unique_key: str | int, default_option: str = 'java'):
    # List of available languages

    selected_language = st.selectbox(label="Select Code Language",
                                     key="language_select_" + unique_key,
                                     options=CODE_LANGUAGES,
                                     index=CODE_LANGUAGES.index(default_option))
    return selected_language


def define_chatGPTModel(unique_key: str | int, default_min_value: float = .2, default_max_value: float = .8,
                        default_temp_value: float = .2,
                        default_step: float = 0.1, default_option="gpt-4o") -> Tuple[str, float]:
    # Dropdown for selecting ChatGPT models
    model_options = [default_option, "gpt-4-turbo", "gpt-4-1106-preview", "gpt-3.5-turbo", "gpt-3.5-turbo-16k-0613"]
    selected_model = st.selectbox(label="Select ChatGPT Model",
                                  key="chat_select_" + unique_key,
                                  options=model_options,
                                  index=model_options.index(default_option))

    # Slider for selecting a value (ranged from 0.2 to 0.8, with step size 0.01)
    # Define the ranges and corresponding labels
    ranges = [(0, 0.3, "Low temperature: More focused, coherent, and conservative outputs."),
              (0.3, 0.7, "Medium temperature: Balanced creativity and coherence."),
              (0.7, 1, "High temperature: Highly creative and diverse, but potentially less coherent.")]

    temperature = st.slider(label="Chat GPT Temperature",
                            key="chat_temp_" + unique_key,
                            min_value=max(default_min_value, 0),
                            max_value=min(default_max_value, 1),
                            step=default_step, value=default_temp_value,
                            format="%.2f")

    # Determine the label based on the selected value
    for low, high, label in ranges:
        if low <= temperature <= high:
            st.write(label)
            break

    return selected_model, temperature


def reset_session_key_value(key: str):
    st.session_state[key] = str(randint(1000, 100000000))


def add_upload_file_element(uploader_text: str, accepted_file_types: list[str], success_message: bool = True,
                            accept_multiple_files: bool = False) -> list[tuple[Any, str]] | tuple[Any, str] | tuple[
    None, None]:
    # Button to reset the multi file uploader
    reset_label = "Reset " + uploader_text + " File Uploader"
    reset_key = reset_label.replace(" ", "_")

    if reset_key not in st.session_state:
        reset_session_key_value(reset_key)

    uploaded_files = st.file_uploader(label=uploader_text, type=accepted_file_types,
                                      accept_multiple_files=accept_multiple_files, key=st.session_state[reset_key])

    if accept_multiple_files:
        if st.button("Remove All Files", key="Checkbox_" + st.session_state[reset_key]):
            reset_session_key_value(reset_key)
            st.rerun()

        uploaded_file_paths = []
        for uploaded_file in uploaded_files:
            if uploaded_file is not None:
                # Get the original file name
                original_file_name = uploaded_file.name

                # Create a temporary file to store the uploaded file
                temp_file_name = upload_file_to_temp_path(uploaded_file)

                uploaded_file_paths.append((original_file_name, temp_file_name))
        if uploaded_files and success_message:
            st.success("File(s) uploaded successfully.")
        return uploaded_file_paths

    elif uploaded_files is not None:
        # Get the original file name
        original_file_name = uploaded_files.name
        # Create a temporary file to store the uploaded file
        temp_file_name = upload_file_to_temp_path(uploaded_files)

        if success_message:
            st.success("File uploaded successfully.")
        return original_file_name, temp_file_name
    else:
        return None, None


def upload_file_to_temp_path(uploaded_file: UploadedFile):
    file_extension = get_file_extension_from_filepath(uploaded_file.name)

    # Create a temporary file to store the uploaded instructions
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
    temp_file.write(uploaded_file.getvalue())
    # temp_file.close()

    return temp_file.name


def process_file(file_path, allowed_file_extensions):
    """ Using a file path determine if the file is a zip or single file and gives the contents back if single or dict mapping the studnet name and timestamp back to the combined contents"""

    # If it's a zip file
    if file_path.endswith('.zip'):
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            folder_contents = {}
            for zip_info in zip_file.infolist():
                if any(zip_info.filename.lower().endswith(ext) for ext in allowed_file_extensions):
                    folder_path = os.path.dirname(zip_info.filename)
                    with zip_file.open(zip_info) as file:
                        file_contents = file.read()
                    folder_contents.setdefault(folder_path, []).append(file_contents)

            for folder_path, files in folder_contents.items():
                concatenated_contents = b''.join(files)
                print(f"Contents of folder '{folder_path}': {concatenated_contents.decode()}")

    # If it's a single file
    else:
        if any(file_path.lower().endswith(ext) for ext in allowed_file_extensions):
            with open(file_path, 'r') as file:
                print("Contents of single file:", file.read())


def choose_preferred_mime(mime_list):
    # Define a priority order for MIME types
    priority_order = [
        "application/octet-stream",
        "application/zip"

    ]

    for mime in priority_order:
        if mime in mime_list:
            return mime

    # Return the first MIME type if none match the priority order
    return mime_list[0]


def get_file_mime_type(file_extension: str):
    # Check if file_extension is prefixed with "." if not add it first
    if not file_extension.startswith("."):
        file_extension = "." + file_extension

    # Define the mapping of file extensions to MIME types
    mime_dict = {}
    lines = mime_types_str.strip().split('\n')
    for line in lines:
        try:
            key, value = line.split()
        except ValueError:
            print("Error splitting line: %s" % line)
            key = None
            value = None

        if key in mime_dict:
            mime_dict[key].append(value)
        else:
            mime_dict[key] = [value]

    # Create a dictionary with preferred MIME types
    preferred_mime_dict = {ext: choose_preferred_mime(mimes) for ext, mimes in mime_dict.items()}

    return preferred_mime_dict.get(file_extension, "application/octet-stream")


def on_download_click(file_path: str, button_label: str, download_file_name: str) -> str:
    file_extension = get_file_extension_from_filepath(download_file_name)
    mime_type = get_file_mime_type(file_extension)
    # st.info("file_extension: " + file_extension + " | mime_type: " + mime_type)

    # file_content = read_file(file_path)
    # Read the content of the file
    with open(file_path, "rb") as file:
        file_content = file.read()

    # st.info("file_path: "+file_path+" | download_file_name: "+download_file_name)
    # st.markdown(file_content)

    # Trigger the download of the file
    return ste.download_button(label=button_label, data=file_content,
                               file_name=download_file_name, mime=mime_type
                               # , key=download_file_name
                               )


def create_zip_file(file_paths: list[tuple[str, str]]) -> str:
    # Create a temporary file to store the zip file
    zip_file = tempfile.NamedTemporaryFile(delete=False)
    zip_file.close()  # Close the file to use it as the output path for the zip file

    with zipfile.ZipFile(zip_file.name, 'w') as zipf:
        for orig_file_path, temp_file_path in file_paths:
            # Get the base file name from the original file path
            base_file_name = os.path.basename(orig_file_path)
            # Add the temporary file to the zip file with the original file name
            zipf.write(temp_file_path, arcname=base_file_name)

    # Return the path of the zip file
    return zip_file.name


def prefix_content_file_name(filename: str, content: str):
    return "# File: " + filename + "\n\n" + content


@st.cache_data
def convert_content_to_markdown(content: str) -> str:
    return md(content)


@st.cache_data
def read_file(file_path: str, convert_to_markdown: bool = False) -> str:
    """ Return the file contents in string format. If file ends in .docx will convert it to json and return"""
    file_name, file_extension = os.path.splitext(file_path)

    if convert_to_markdown:
        with open(file_path, mode='rb') as f:
            # results = mammoth.convert_to_markdown(f)
            results = mammoth.convert_to_html(f)
            contents = convert_content_to_markdown(results.value)
        # contents = results.value
    elif file_extension == ".docx":
        # read in a document
        my_doc = docx.Document(file_path)

        # Find any tables and replace with json strings
        tmp_file = convert_tables_to_json_in_tmp__file(my_doc)

        # coerce to JSON using the standard options

        # contents = simplify(my_doc)

        # contents = textract.parsers.process(file_path)
        # print("Extracting contents from: %s" % tmp_file)
        contents = textract.process(tmp_file).decode('utf-8')
        os.remove(tmp_file)

    else:
        with open(file_path, mode='r') as f:  # TODO: Make sure you want to open with rb option
            contents = f.read()

    return str(contents)

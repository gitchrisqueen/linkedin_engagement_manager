# Changelog

## [0.9.0](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.8.0...v0.9.0) (2026-06-29)


### Features

* **automation:** per-user geo/timezone/locale spoofing for LinkedIn login ([e24a5b7](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/e24a5b7e9ca35759cc6f94a373ab4a3c73c8a5f0))
* **automation:** per-user geo/timezone/locale spoofing for LinkedIn login ([f6f8acc](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/f6f8acc5084fa6bc8fdc799d9d0b2af3d5fd4c2e))

## [0.8.0](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.7.1...v0.8.0) (2026-06-29)


### Features

* **ui:** embed video + carousel in post preview card ([8663f39](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/8663f39d413a96dd31f2cb2d9c9f1641e6835e72))
* **ui:** embed video + carousel in post preview card ([ee90508](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/ee9050848d33b8fcfe70a0c98c6d0a9a63f0feee))

## [0.7.1](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.7.0...v0.7.1) (2026-06-28)


### Bug Fixes

* **assets:** make worker-written media reliable + backfill missing assets ([8364817](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/83648172f7f89d510dc3d30144c054c7477c5265))
* **assets:** reliable worker media writes + missing-asset backfill ([52271f2](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/52271f2ccf9eff8b2e1f0d90620b87394751d19c))

## [0.7.0](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.6.0...v0.7.0) (2026-06-26)


### Features

* **video:** premium video tiers with a credit system ([e346e72](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/e346e72eb2ca5b4271dd8f3caa21159f45cc4c6a))
* **video:** premium video tiers with a credit system ([a87b3de](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/a87b3debe931dfa924e8ed828acc6d228eee29ec))

## [0.6.0](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.5.0...v0.6.0) (2026-06-25)


### Features

* **media:** Gen-4 Turbo migration, profile-aligned prompts, variant review tool ([f36e685](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/f36e685b0390a8b3ead1734457046aefe0f08de8))
* **media:** migrate to Gen-4 Turbo, profile-aligned prompts, variant tool ([23006cf](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/23006cfc4e15988f9d198de17942cb5854330532))


### Bug Fixes

* **script:** surface API errors + detect not-deployed (404/405) in variant script ([b4118c1](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/b4118c1942edf4c34cf96ff444ad75909b39696b))

## [0.5.0](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.4.0...v0.5.0) (2026-06-25)


### Features

* **assets:** purge post media after publish to bound the assets volume ([#148](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/148)) ([98dacbb](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/98dacbb6b1dcf4c4e9d4707b80a4a967da068f11))

## [0.4.0](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.3.2...v0.4.0) (2026-06-25)


### Features

* **api:** add /api/admin/regenerate-video (asset-only) ([#146](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/146)) ([06458a0](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/06458a0b9049a1b53b26da7f1367b5a45a709d9e))

## [0.3.2](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.3.1...v0.3.2) (2026-06-25)


### Bug Fixes

* **prod:** shared persistent volume for generated assets ([#144](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/144)) ([fdf8fe4](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/fdf8fe4517a2d5d2afbaebacfc34f05905fa6376))

## [0.3.1](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.3.0...v0.3.1) (2026-06-25)


### Bug Fixes

* **api:** make /api/assets public so LinkedIn can fetch post media ([#142](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/142)) ([c67b495](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/c67b495720062e7ceb9f0b6b8d8bcec8e16c632e))

## [0.3.0](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.2.0...v0.3.0) (2026-06-25)


### Features

* **config:** add PUBLIC_BASE_URL taking precedence over ngrok URLs ([#140](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/140)) ([46222f4](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/46222f431abbef636c9ce19bdbb1a6dbf6f39359))

## [0.2.0](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.1.3...v0.2.0) (2026-06-25)


### Features

* **ui+prod:** app title; run celery/flower from image (drop src bind-mount) ([#138](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/138)) ([5a66105](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/5a66105992b765ce848e78bd1894f2fc818cc277))

## [0.1.3](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.1.2...v0.1.3) (2026-06-25)


### Bug Fixes

* **prod:** drop dev src bind-mount that masked the built SPA ([#136](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/136)) ([a90eff1](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/a90eff174dc28d2f9581a4732fc33d543a3ff152))

## [0.1.2](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.1.1...v0.1.2) (2026-06-25)


### Bug Fixes

* **build:** ensure SPA dist is in the image; expose MySQL on loopback ([#134](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/134)) ([46166bc](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/46166bce66c38b76de5c42e225b05a78923c067b))

## [0.1.1](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/compare/v0.1.0...v0.1.1) (2026-06-25)


### Bug Fixes

* **build:** commit UI package-lock.json (Docker npm ci requires it) ([#132](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/132)) ([7d53fa2](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/7d53fa22fa1449be0241ad9932c5949454ecf5e2))
* **ci:** correct trivy-action tag (v0.28.0) in release workflow ([#129](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/129)) ([38c8aea](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/38c8aeaaad4ff2025399eea678c046c86cde15ce))
* **ci:** remove advisory Trivy scan blocking the release build ([#131](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/131)) ([cbc6e8a](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/cbc6e8a60d5fbbb69bf8109bedc6ad41229e055b))
* **ops:** logs dir ACL for mixed-uid containers + dynamic backup volume ([#133](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/133)) ([077ea27](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/077ea277586e79d5f2101c2cf5d4773b89888242))

## 0.1.0 (2026-06-25)


### Features

* add Replicate avatar training with Stripe credit system ([f2ca54f](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/f2ca54fff7dd993b9e3fb1a009992e7fcf075a94))
* **ai/video:** add Perplexity Sonar research and Pexels stock video fallback ([fa585d1](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/fa585d1eb67f147b3625990bbceaf0bdb311d178))
* **ai/video:** Perplexity Sonar research + Pexels stock video fallback ([3399f08](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/3399f0804c802172c2dc3fc53f002cf741d5685c))
* **billing/tests:** fix Stripe duplicate subscription on upgrade, add coverage ([66f1e45](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/66f1e45f5cb85c4b4a5e56a41bf7d5bd708c6271))
* carousel slides (Pillow), video URL fix, LinkedIn markdown cleanup ([d6683c1](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/d6683c1f1f6c230e4770277cd7437bf8913dc338))
* carousel slides with Pillow, video URL fix, LinkedIn markdown cleanup ([c0bfe8f](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/c0bfe8ff8c804fa8fd9044b1282d28ecaea90958))
* **carousel:** 5 distinct template layouts + AI generation in manual scheduler ([0866500](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/0866500296888d5f17bdb430d1a67c3dc073a5d6))
* **coverage:** raise coverage 40% → 58% — exclusions + 160 new unit tests ([a1ff690](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/a1ff690d1e2868a4121027e14524c89e09992877))
* **coverage:** raise coverage 58% → 67% — 175 new unit tests across 5 files ([93f4bc9](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/93f4bc9b0ae518c0cd9162b74f04754147f5576a))
* **deploy:** add Hostinger VPS deploy stack with Cloudflare Tunnel ([932cc37](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/932cc3738f9795179d32b5a50396785f38552b23))
* **deploy:** Hostinger VPS deploy pipeline with Cloudflare Tunnel ([0674af3](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/0674af3ed547a61714289d24d2ce5b9f6065fe80))
* **deploy:** make vps_bootstrap.sh a guided idempotent first-run ([67d2912](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/67d29126314c1146d062a1c1ae8ac406b854fa73))
* **m0:** add developer context files and full CI/CD suite ([f300e10](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/f300e1013688399a2c5cc88bbb4fa27caf86f311))
* **m0:** Developer context files and full CI/CD suite ([616bedb](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/616bedb3ba618df60ff3066bd626b80bba33dca6))
* **m0:** Developer context files and full CI/CD suite ([616bedb](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/616bedb3ba618df60ff3066bd626b80bba33dca6))
* **m1:** infrastructure modernization — standalone-chrome, LiteLLM, PostHog ([662e623](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/662e6236c9748d5b252b256f0bc9545604af8047))
* **m1:** Infrastructure modernization — standalone-chrome, LiteLLM, PostHog ([04c2123](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/04c21234e15c798126809544ec3ca479218c8ad5))
* **m1:** Infrastructure modernization — standalone-chrome, LiteLLM, PostHog, Ollama Cloud ([04c2123](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/04c21234e15c798126809544ec3ca479218c8ad5))
* **m1:** switch LiteLLM to Ollama-first model routing ([11a3ea0](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/11a3ea04d084ee9bbcdc57f9367e7285cea51def))
* **m2:** Real unit and integration tests replacing pass-body stubs ([0068538](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/0068538a1d70eed2d33aa7d519ec7a72ba5f0df8))
* **m2:** write real unit and integration tests replacing pass-body stubs ([9ac3839](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/9ac38395949bd23812630d51ea7188e49de1db24))
* **m4:** React + TailwindCSS SPA — Dashboard, Schedule, Review, Account, LinkedIn Preview ([c695483](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/c69548384d3f6329b584a0aae9fd00a9935a018e))
* **m4:** React + TailwindCSS SPA with 4 pages and LinkedIn preview ([3d22aa2](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/3d22aa202e7cb84ae570653d6be951219acb1b86)), closes [#17](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/17) [#18](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/18) [#19](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/19) [#20](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/20) [#21](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/21) [#22](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/22) [#23](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/23)
* **m4:** replace Streamlit with React SPA served via FastAPI ([#85](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/85)) ([0ae657d](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/0ae657dd3050cfcefec23865352dde21194a3ee0))
* **m5:** Feature completion — carousel handlers, article posting, active users, invite logging ([439f504](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/439f504301d6d95d8f3a125c67668408d782ddf3))
* **m5:** feature completion — carousel handlers, article posting, invite logging, user update ([c8742be](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/c8742be3bb60a6d1af846985142bb0f361259840)), closes [#24](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/24) [#25](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/25) [#28](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/28) [#29](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/29) [#31](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/31)
* Review Posts read-only for posted status, CapSolver CAPTCHA, codecov config ([bb62cf5](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/bb62cf5296697e6d59936ee6fa16679f17c1e208))
* **tests:** CapSolver CAPTCHA e2e + /post_url endpoint + codecov config ([f683f81](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/f683f81230c2f99b7b1de8c25a9f1094317838fa))
* **ui:** complete SaaS landing page, protected routing, schedule improvements ([#86](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/86)) ([8d6ca6c](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/8d6ca6cff750f61fd0c0dc9109c57d432282f9f1))


### Bug Fixes

* address remaining CodeQL alerts and broken integration test ([796190e](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/796190e0e9b6a73aa0e3ac2ba12be240c59ecca4))
* **auth/ui/infra:** account save, OAuth email handoff, Docker UI build, DM/carousel features ([#94](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/94)) ([76b0c09](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/76b0c0953a33d75b413b3e428276e4668f15367c))
* **avatar:** correct Replicate training API call — create destination model first ([22877d7](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/22877d76e702c157dc5b6c31c9d0213f8402e09e))
* **avatar:** update destination hardware SKU to gpu-l40s ([d6e32db](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/d6e32db420c31b22f321b9d22e77d41a170f35ce))
* **avatar:** upload ZIP via replicate.files.create() to avoid SSL TLS errors ([b575bdc](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/b575bdcfc06d388fe8de04299f827974283af276))
* **backend:** deprecated API stubs, active user detection, geolocation, logging, integration tests ([#87](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/87)) ([070ad68](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/070ad6810bd5a60c1e5ba3acfc08695d11a57ddc))
* **carousel+scheduler+ops:** URL-slide upload, inactive-user pre-post skip, cascade deletes, selenium healthcheck ([a07df7c](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/a07df7c727fa95a6c9d2c5a7c85f087bfa672d5d))
* **carousel:** redesign slide renderer — large fonts, visual hierarchy, clean chars ([2c79ced](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/2c79ced823debc9f372315ce272a018e4c6bbc6f))
* **carousel:** URL slides bypassed to upload_media instead of Pexels fallback ([5901ad9](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/5901ad9dfebf483f8e69069205e6235a2df37750))
* **ci:** resolve CodeQL warnings and integration test failures ([0326c40](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/0326c40deca9ed42751ada3c2f73d914f72d1eda))
* **ci:** resolve E2E test failures and CodeQL security alert ([4dec003](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/4dec003588b1a603bc8495d9d1493e92a557d998))
* **codecov:** make project coverage informational, use auto baseline ([5d6e06c](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/5d6e06cba8efd5bb144fca6c43378a21f4f8b2e4))
* correct /api/assets URL path and add backward-compat redirect ([3413974](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/3413974e24cbb661bcb997b6831c0af6037a125b))
* correct avatar DB connection pattern and seed blog/sitemap from API ([ce58da3](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/ce58da3765c3e8bde93b754657bc33ef0ad2d1d6))
* **db+scheduler:** cascade-delete user FKs and skip pre-post tasks for inactive users ([d677c71](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/d677c7138f4722e4149f3fbd44e78c0aef5bf0b3))
* **deploy:** correct GHCR namespace in .env.prod.example ([1765919](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/176591901efc81d1e1fdb930390c3b893c6aeed3))
* **docker:** disable flower persistence to fix corrupted shelve DB at startup ([#89](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/89)) ([eeb39f0](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/eeb39f0eef57279f904fa59f0a21fc838da9236a))
* **flower:** remove hardcoded persistence flags causing startup crash ([#90](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/90)) ([00d1424](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/00d1424aa6466533d76f56746dbafec88bf253ef))
* **infra/auth:** litellm healthcheck, LinkedIn OAuth initiation, dynamic redirect URL, PostHog silencing ([#88](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/88)) ([685fbcd](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/685fbcde7445635081762249bd6dc81b768e5fed))
* **m0:** code review agent, workflow bug fixes, and permissions hardening ([723da11](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/723da115ada082777be792da71cb030e8e8bcf7d))
* **m1:** use custom_callbacks for complexity router in LiteLLM config ([5a38c01](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/5a38c015d0bde7a826d6b133813780488e40d87e))
* **m2:** make all 88 unit tests pass with production code fixes ([c2b250a](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/c2b250a71c6a38c90b690271be4e8f41ee346a04))
* **m3:** Critical bug fixes — media type, token expiry, scraper prefix, hardcoded data ([057829f](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/057829f9f70247a958c7bd6ec3bafc595a17e8e1))
* **m3:** fix 4 critical bugs in poster, scrapper, db, and test files ([3a771de](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/3a771de02e2e672adffed6e2c84ac3a6f905f0b6)), closes [#29](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/29) [#30](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/30) [#32](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/32) [#33](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/33)
* **ngrok/run:** correct all port and URL references in templates and run.sh ([#93](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/93)) ([7f6f70d](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/7f6f70d9231578d2be682dbe25fcf9f9d3a49cb6))
* **ngrok:** fix ERR_NGROK_108 session conflict and STREAMLIT_PORT reference ([#91](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/issues/91)) ([ac0d506](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/ac0d5069563d6805ea05c9fc956d64e594f81e85))
* **observability:** repair PostHog event delivery and LinkedIn login error visibility ([b4a2b20](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/b4a2b20bcbbd3d218148d82df01b775a77a479a2))
* **observability:** repair PostHog event delivery and LinkedIn login error visibility ([c63ac37](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/c63ac375ac5553f167ab832225badd6bc5173e47))
* **ops:** extend run.sh Celery restart check to cover celery_worker_selenium ([3b329af](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/3b329af815df7c4d253a761b026dc692cf5e39d1))
* **ops:** fix selenium worker healthcheck hostname and timeout ([ecbef6c](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/ecbef6ceb2119d284139a935d8adcdb276251160))
* **ops:** stop Selenium task collisions + fix 3 log errors from last 48h ([80b47d0](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/80b47d0a746c7c7785b7ed87f2eba986a8824ab8))
* **ops:** stop Selenium task collisions + fix 3 recurring log errors ([529f3f2](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/529f3f29ecfbebc5c6ad1d2827e9e18dd77ddfbd))
* **pipeline/security:** fix post schedule pipeline, auth security, and billing ([950ef0f](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/950ef0f015fdd19141521d437a2903b1f5b89a0a))
* **pipeline/security:** fix post schedule pipeline, auth security, and billing correctness ([04e2290](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/04e2290bb45e708ec1cd4aace2a731d5ad633d48))
* **posting:** repair token_expiry SQL bug, add orphaned-post recovery, fix beat healthcheck ([6f5f8ee](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/6f5f8ee2d0efedaaf06f30bf6d952f13f5595bad))
* resolve CodeQL security alerts and update GitHub Actions to Node.js 24 ([e3591d4](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/e3591d482920b7bb9bf3ba27988e2e9e90ca3271))
* resolve CodeQL security alerts and update GitHub Actions to Node.js 24 ([866e411](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/866e411f79c875dbe31f77e476de27f52d203a11))
* **security:** clear remaining CodeQL path-injection and static-analysis alerts ([de8d316](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/de8d316b5568f66d6c06c14ad72869b19eb699d4))
* **security:** resolve 8 CodeQL alerts introduced by new test files ([12cbb51](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/12cbb516a37bb9d542e3ea07f40eca8a28cfd346))
* **security:** resolve CodeQL alerts and make codecov components informational ([ce7cbd4](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/ce7cbd4aa1126eaaaf60c80c5b54fb35cffee5d7))
* **security:** resolve CodeQL alerts in CAPTCHA integration code ([fd6d5d4](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/fd6d5d4ed56ac6a250d92c01ef986d3b7f781a04))
* **test:** correct Stripe webhook integration test for avatar credits ([5809e75](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/5809e75cfb4afeda25f3abe5674a02bb4039e6cc))
* **test:** defer api.main import to fixtures to avoid collection-time OpenAI key ([6c00dce](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/6c00dce7f54535bde353fea626571b64b721957d))
* **test:** pin datetime.now() to Monday in content-plan unit tests ([5fd8506](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/5fd8506682ceb4bc4614aa06dfa3d08fb7a5bd83))
* **tests:** correct mock patch locations and CI env vars for integration tests ([f7e7645](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/f7e764591ebfff470a2f1bf763fe84ffc4f6c419))
* **test:** use startswith with trailing slash for Stripe URL assertion ([5507da8](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/5507da8d9b62ae2361d8d5fc5ead784383f9c1a2))
* **timezone:** end-to-end timezone correctness for post scheduling and display ([5d39749](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/5d39749599deb27b1c405cb7d5a5330e25249584))
* **timezone:** end-to-end timezone correctness for post scheduling and display ([b427093](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/b427093741b4f4094c91430c900a6ec3fc15ee30))
* update test to use timezone-aware datetime and ignore .vscode/mcp.json ([e2172d4](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/e2172d42d07456684a2b0894303b53d0ef155792))
* **webhook:** robust checkout.session.completed + charge.refunded handling ([c027587](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/c0275879ef1ae14860b1282acf8ae9bf3a245cdd))


### Documentation

* **deploy:** add manual go-live setup checklist ([b1d61ca](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/b1d61ca4df5b7aa7efa65bd1b846f15c1ca290d0))
* update README for React/FastAPI/LiteLLM/PostHog stack ([76b0c09](https://github.com/christopherqueenconsulting/linkedin_engagement_manager/commit/76b0c0953a33d75b413b3e428276e4668f15367c))

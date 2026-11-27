# Backend TODO

## Before the backend foundation is considered complete

- [ ] Upload sample TXT, PDF, and DOCX files end to end; confirm each is stored in Neon with embeddings and correct line/page/paragraph references.
- [ ] Test similarity retrieval with known questions and tune the unsupported-answer distance threshold.
- [ ] Exercise chat for supported and unsupported questions with provider keys supplied through the frontend BYOK settings endpoint.
- [ ] Verify deletion removes the database document, chunks, embeddings, and original upload; check missing IDs and filesystem failures.
- [ ] Review upload limits, malformed-file errors, and handling of Cloudflare/provider errors.
- [ ] Add a database migration path so schema changes do not depend on `create_all` at startup.
- [ ] Decide durable original-file storage before deployment; current uploads are local to the backend machine.
- [ ] Add server authentication and request protections before exposing the API to a client or the public internet.
- [ ] Add integration and regression tests for upload, retrieval, chat citations/fallback, session-only API keys, and deletion.
- [ ] Update deployment and client setup instructions after choosing production hosting and file storage.

# goodnews frontend

Vue 3 Composition API + TypeScript + Vite + Pinia + Vue Router + Element Plus.
All business requests live in `src/api/`; pages only compose components and
composables. The social-platform page is `src/views/SocialView.vue`, backed by
`src/stores/social.ts`, `src/stores/socialAuth.ts` and `src/api/social.ts`.
Platform cards include login, logout and account-switch buttons plus automatic
auth-status refresh. The social page can create a background full-comment job and
download the result as xlsx, md or txt.

## Run

```bat
cd /d D:\goodnews\frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. In development, Vite proxies `/api` to
`http://127.0.0.1:8010`, so no frontend secret or CORS token is needed.

## Verify

```bat
npm run typecheck
npm run build
```

Set `VITE_API_BASE_URL` only when the API is served from another origin
(see `.env.example`). Never place API keys in frontend variables.

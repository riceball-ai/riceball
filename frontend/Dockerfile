FROM node:22-trixie-slim AS base

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app


# PWA

FROM base AS build-pwa

RUN mkdir -p /pnpm && chown -R node:node /app /pnpm

COPY --chown=node:node package.json pnpm-lock.yaml .

USER node

RUN --mount=type=cache,id=pnpm,target=/pnpm/store,uid=1000,gid=1000 pnpm install --frozen-lockfile \
    && pnpm config set store-dir /pnpm/store --global

COPY --chown=node:node . .

RUN pnpm run generate


FROM nginx:alpine AS pro

COPY nginx.conf.template /etc/nginx/templates/default.conf.template

COPY --from=build-pwa /app/.output/public /usr/share/nginx/html


# SSR

FROM base AS build-ssr

ARG API_BASE_URL=http://backend:8000
ENV API_BASE_URL=$API_BASE_URL

RUN mkdir -p /pnpm && chown -R node:node /app /pnpm

COPY --chown=node:node package.json pnpm-lock.yaml .

USER node

RUN --mount=type=cache,id=pnpm,target=/pnpm/store,uid=1000,gid=1000 pnpm install --frozen-lockfile \
    && pnpm config set store-dir /pnpm/store --global

COPY --chown=node:node . .

RUN pnpm run build


FROM node:22-alpine AS ssr-runner

WORKDIR /app

COPY --from=build-ssr /app/.output /app

EXPOSE 3000

CMD [ "node", "./server/index.mjs" ]


# DEV

FROM base AS dev

RUN mkdir -p /pnpm && chown -R node:node /app /pnpm

COPY --chown=node:node package.json pnpm-lock.yaml ./

USER node

RUN --mount=type=cache,id=pnpm,target=/pnpm/store,uid=1000,gid=1000 pnpm install --frozen-lockfile \
    && pnpm config set store-dir /pnpm/store --global

COPY --chown=node:node . .

EXPOSE 3000

CMD [ "pnpm", "dev" ]
# AI Assistants Frontend

A modern web application for interacting with AI assistants, built with Nuxt.js 3, Vue 3, and TypeScript.

## Features

- **Authentication System**: Secure user authentication with email verification
- **Assistant Management**: View and select from available AI assistants
- **Real-time Chat**: Interactive conversations with AI assistants
- **Responsive Design**: Modern UI with Tailwind CSS and shadcn-vue components

## Tech Stack

- **Framework**: Nuxt.js 3
- **Language**: TypeScript
- **UI Library**: Vue 3 + shadcn-vue
- **Styling**: Tailwind CSS
- **State Management**: Pinia
- **API Communication**: Custom API composable

## Setup

Make sure to install dependencies:

```bash
# npm
npm install

# pnpm
pnpm install

# yarn
yarn install

# bun
bun install
```

## Development Server

Start the development server on `http://localhost:3000`:

```bash
# npm
npm run dev

# pnpm
pnpm dev

# yarn
yarn dev

# bun
bun run dev
```

## Pages

- **Home (`/`)**: Landing page
- **Sign In (`/sign-in`)**: User authentication
- **Sign Up (`/sign-up`)**: User registration
- **Email Verification (`/verify-email`)**: Email verification process
- **Assistants (`/assistants`)**: View and select AI assistants
- **New Chat (`/chat/{assistantId}`)**: Start new conversation with assistant
- **Continue Chat (`/chat/{assistantId}/{conversationId}`)**: Continue existing conversation

## Routing Structure

The application uses a hierarchical routing structure:

- `/chat/{assistantId}` - Creates a new conversation with the specified assistant
- `/chat/{assistantId}/{conversationId}` - Continues an existing conversation

This design allows:
- Clear identification of which assistant is being used
- Proper conversation history management
- Bookmarkable conversation URLs
- Easy navigation between different conversations

## API Endpoints

The frontend expects the following API endpoints:

- `GET /api/assistants` - Get list of available assistants
- `GET /api/assistants/:id` - Get specific assistant details
- `GET /api/chat/sessions/:assistantId` - Get or create chat session
- `POST /api/chat/messages` - Send message to assistant

## Production

Build the application for production:

```bash
# npm
npm run build

# pnpm
pnpm build

# yarn
yarn build

# bun
bun run build
```

Locally preview production build:

```bash
# npm
npm run preview

# pnpm
pnpm preview

# yarn
yarn preview

# bun
bun run preview
```

Check out the [deployment documentation](https://nuxt.com/docs/getting-started/deployment) for more information.

# yarn
yarn build

# bun
bun run build
```

Locally preview production build:

```bash
# npm
npm run preview

# pnpm
pnpm preview

# yarn
yarn preview

# bun
bun run preview
```

Check out the [deployment documentation](https://nuxt.com/docs/getting-started/deployment) for more information.
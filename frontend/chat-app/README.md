# Varta Bharat: mobile app

The mobile frontend for Varta Bharat, built with Expo, React Native and TypeScript.

All data is mocked for now, so you do not need the backend to run it. The real API and sync layer will connect later.

## Run it

    npm install
    npx expo start

Then do one of these:

- Scan the QR code with the Expo Go app on your phone
- Press `a` to open an Android emulator
- Press `i` to open an iOS simulator (Mac only)

## Folder guide

- `src/app`: all screens (file-based routing, one file per screen)
  - `(auth)`: sign-in and first launch screens
  - `(tabs)`: the main tabs (chats, people, communities, settings)
  - `admin`, `group`, `community`, `invite`, `settings`: feature screens
- `src/components`: reusable UI pieces (buttons, avatars, chat bubbles, etc.)
- `src/theme`: colors, fonts and spacing
- `src/data`: mock data (replaced by the real API later)
- `src/state`: app state
- `src/auth`: sign-in state

## Status

UI is complete with mock data. Backend connection is not done yet.
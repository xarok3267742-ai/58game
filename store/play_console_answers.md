# Play Console Answers

Use this as a copy/paste aid for Play Console. Final answers are still the developer account owner's responsibility.

## App Details
- App name: Шаурма 58
- Default language: Russian (`ru-RU`)
- App or game: Game
- Category: Casual
- Free or paid: Free
- Contains ads: No
- In-app purchases: No

## Store Listing
- Title: `fastlane/metadata/android/ru-RU/title.txt`
- Short description: `fastlane/metadata/android/ru-RU/short_description.txt`
- Full description: `fastlane/metadata/android/ru-RU/full_description.txt`
- Release notes: `fastlane/metadata/android/ru-RU/changelogs/1.txt`
- Play app icon: `store/play_icon.png`
- Feature graphic: `store/feature_graphic_concept.png`
- Screenshots: use the curated upload order in `store/play_listing_ru.md`.

## Privacy Policy
- Host `store/privacy_policy.html` on a public, non-geofenced, non-PDF URL.
- Paste the hosted URL into Play Console.
- Make sure the Play Console developer contact email is filled in, because the privacy policy refers users to that contact mechanism.

## App Access
- Does the app require login, membership, location-based access or special credentials? No.
- Are all app features available to reviewers immediately after install? Yes.
- Reviewer instructions: open the app, tap through onboarding and start any unlocked shift; no account, server, code, QR, payment or network connection is required.

## Data Safety
- Does the app collect or share any required user data types? No.
- Is all user data collected encrypted in transit? Not applicable; no user data is transmitted.
- Does the app provide a way for users to request data deletion? Not applicable for server data; there is no account or server storage. Users can delete local progress in the app settings, by clearing app data or by uninstalling the app.
- Accounts/login: No.
- Data shared with third parties: No.
- Data processed ephemerally: No data collected.
- Data collection optional/required: No data collected.

## Permissions
- Dangerous permissions: none.
- INTERNET permission: absent.
- Background location, contacts, SMS, phone, files, camera, microphone: not used.

## Content Rating
- Violence: No.
- Fear/horror: No.
- Sexual content/nudity: No.
- Profanity: No.
- Controlled substances: No.
- Gambling or simulated gambling: No.
- User-generated content or user communication: No.
- Location sharing: No.
- Digital purchases: No.
- Ads: No.

## Other App Content Declarations
- News app: No.
- Health app: No.
- Government app: No.
- Financial features: No.
- COVID-19 contact tracing or status app: No.
- VPN service: No.
- Background location: No.
- Restricted content requiring reviewer credentials: No.

## Target Audience
- Not specifically directed at children.
- Recommended Play Console target age selection: 13-15, 16-17, 18+.
- Do not opt into Designed for Families for v1.

## Release
- Upload artifact: `app/build/outputs/bundle/release/app-release.aab` after configuring upload signing.
- Current local AAB without signing env vars is unsigned; do not upload it before configuring signing.
- First rollout path: internal testing, then closed testing if required, then staged production rollout.

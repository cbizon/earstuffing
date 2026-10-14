# Earstuffing Notes privacy policy

Earstuffing Notes is a personal tool for recording short voice notes while
listening to podcasts in the car.

- **What it records:** audio from the car or phone microphone, only between
  opening the note screen and pressing Stop or Discard (or after ten
  minutes, whichever comes first). Discarded recordings are deleted.
- **What else it reads:** the title, show name and playback position of the
  podcast that is playing when you press Record. It uses Android's notification
  access only to read this media information; it does not read notifications.
- **Where data goes:** each recording and its podcast details are uploaded to
  a Cloudflare R2 storage bucket that you configure in the app with your own
  credentials. Nothing is sent anywhere else. The app has no analytics,
  advertising or tracking.
- **What stays on the phone:** your R2 settings, and recordings until they
  upload. Uninstalling the app deletes both.
- **Sharing:** the developer does not receive, sell or share any data. What
  happens to recordings in your bucket is up to you.

Questions: open an issue at https://github.com/cbizon/earstuffing.

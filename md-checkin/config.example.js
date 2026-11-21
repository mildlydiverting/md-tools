// Copy this file to config.js (which is gitignored) and add your key.
// The key can edit your whole Workflowy: never commit or share config.js.
// Copy the key from Keychain with:
//   security find-generic-password -s WORKFLOWY_API_KEY -w | pbcopy
window.CHECKIN_CONFIG = {
  workflowyKey: "",
  windowDays: 14   // how far back to look for slipping tasks
};

# Two-iPhone sync test (Quinn + Taryn)

Before you start: the PC is on, Tailscale is **on** on both iPhones (Taryn must be in the tailnet or have the PC shared with her), and both have Use It Up added to the Home Screen.

| # | Who | Do this | Expected result |
|---|-----|---------|-----------------|
| 1 | Quinn | More → Shared pantry. Check the status line, then tap **Copy invite link** and send it to Taryn (Messages is fine). | Status says **Last synced: \<time\>**. The button changes to "Copied ✓". |
| 2 | Taryn | Tap the link and open it in Safari. Then do the same from the Home Screen app (paste the link into Safari if iOS opens it in the browser instead). | A green-bordered card appears: **"Join the shared pantry?"** with the server address, plus a note that any items already on her phone will be added. |
| 3 | Taryn | Tap **Join**. | A "Joined — syncing…" message appears. Within a few seconds Quinn's items appear in Taryn's Pantry, and More → Shared pantry shows **Last synced: \<time\>**. |
| 4 | Quinn | Add an item called **Sync test** (Add → name → Save). | It appears on Quinn's Pantry right away. |
| 5 | Taryn | Switch away from the app and back again, or wait up to 1 minute. | **Sync test** appears on Taryn's Pantry. |
| 6 | Taryn | Tap 😋 on **Sync test**. Quinn then switches away from the app and back. | It disappears on both phones and shows in More → Last 30 days on both. |
| 7 | Quinn | Turn **Tailscale off** on the iPhone. Add **Offline test**. Wait about 11 minutes, then open More. | The item stays on Quinn's phone. The status says **Not synced** and a ⚠️ warning says sync has failed for more than 10 minutes. Taryn does **not** see the item yet. |
| 8 | Quinn | Turn **Tailscale back on** and switch away from the app and back. | Within a few seconds the status returns to **Last synced: \<time\>** and the warning goes away. **Offline test** appears on Taryn's phone the next time she opens the app. Then delete it on either phone. |

If a step fails, run More → Diagnostics on the failing phone and tap **Copy results**. Send those results along with the step number.

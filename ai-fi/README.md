# AI-FI

The site keeps edits in browser `localStorage` so ratings can be changed without a backend. Those local values are not part of the Git repository until they are exported and applied.

## Save and commit ratings

1. Start the local development server from this `ai-fi` directory:

   ```sh
   node scripts/dev-server.mjs
   ```

2. Open <http://localhost:8765>, make rating changes, then choose **About → Save to repository**. The button applies the browser's ratings and finish dates directly to `app.js`.

Browser storage belongs to the exact host and port. If the existing ratings were entered at, for example, `http://localhost:8000`, stop the old server and run `node scripts/dev-server.mjs 8000`, then open that same URL.

3. Review the changes:

   ```sh
   git diff -- app.js
   ```

4. Commit and push normally.

Removing a book's rating also clears its finish date and marks it unread. The importer replaces `DEFAULT_RATINGS` with the exported ranking and updates every book's canonical `readDate`, so both parts of that removal are committed.

If the site is running through a different static server, the button downloads a JSON file instead. Apply it manually with:

```sh
node scripts/import-reading-data.mjs ~/Downloads/ai-fi-reading-data-YYYY-MM-DD.json
```

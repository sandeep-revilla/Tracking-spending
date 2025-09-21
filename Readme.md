# Live Expense Tracker (Streamlit + Google Sheets)

This app reads a Google Sheet using a Google service account and displays interactive spending dashboards.

## How to use

1. Create a Google service account and download the JSON key.
2. Share your Google Sheet with the service account email (Viewer permission).
3. Add the service account JSON to Streamlit Cloud secrets (key: `gcp_service_account`).
4. Deploy this repo on Streamlit Cloud.
5. Open the app, enter your Google Sheet ID and worksheet name in the sidebar.

## Notes

- The app caches sheet reads for performance; use the Refresh button to force reload.
- Keep the service account JSON secret; do not commit it to Git.

# Privacy

Health OS is local-first software. There is no Health OS server.

- Your health records are fetched directly from your health system's patient-access
  API to your own computer and are stored only there.
- The developer receives, stores, and can access none of your data.
- OAuth credentials and private keys are stored in your operating system's keychain.
- Access to your record is read-only; Health OS never writes to your medical record.
- Optional AI-powered skills send selected record context to a model API under your
  own account and control. The skill states what would be sent before it runs. Your
  data is then subject to that provider's terms under your agreement with them
  (e.g., zero-data-retention options on your API account).

Questions: dipakrkrishnan@gmail.com

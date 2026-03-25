// Development: points to local backend
// Production: points to Railway deployment
// Update PROD_URL after deploying to Railway
const DEV_URL = "http://localhost:8000";
const PROD_URL = "https://ethical-ai-checker.up.railway.app";

export const API_BASE_URL = __DEV__ ? DEV_URL : PROD_URL;

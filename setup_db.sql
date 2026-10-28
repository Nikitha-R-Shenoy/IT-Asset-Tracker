CREATE DATABASE IF NOT EXISTS it_asset_tracker_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

-- Create a least-privilege application user separately with a unique password,
-- then grant that user privileges on it_asset_tracker_db.*.

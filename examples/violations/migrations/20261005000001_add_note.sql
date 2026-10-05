-- Added by hand, never hashed: atlas migrate validate reports a checksum mismatch.
ALTER TABLE `orders` ADD COLUMN `note` text NULL;

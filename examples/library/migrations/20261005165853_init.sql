-- Create "jobs" table
CREATE TABLE `jobs` (
  `job_id` varchar NOT NULL,
  `display_name` varchar NOT NULL,
  `kind` varchar NOT NULL,
  `grace_days` integer NOT NULL,
  `last_run_time` datetime NULL,
  `create_time` datetime NOT NULL,
  `update_time` datetime NOT NULL,
  `etag` varchar NOT NULL,
  PRIMARY KEY (`job_id`)
);
-- Create "operations" table
CREATE TABLE `operations` (
  `operation_id` varchar NOT NULL,
  `kind` varchar NOT NULL,
  `shelf_id` varchar NOT NULL,
  `done` boolean NOT NULL,
  `result_path` varchar NULL,
  `exported_count` integer NULL,
  `error_message` varchar NULL,
  `create_time` datetime NOT NULL,
  `update_time` datetime NOT NULL,
  PRIMARY KEY (`operation_id`)
);
-- Create "shelves" table
CREATE TABLE `shelves` (
  `shelf_id` varchar NOT NULL,
  `display_name` varchar NOT NULL,
  `genre` varchar NOT NULL,
  `create_time` datetime NOT NULL,
  `update_time` datetime NOT NULL,
  `etag` varchar NOT NULL,
  PRIMARY KEY (`shelf_id`)
);
-- Create "books" table
CREATE TABLE `books` (
  `shelf_id` varchar NOT NULL,
  `book_id` varchar NOT NULL,
  `title` varchar NOT NULL,
  `author` varchar NOT NULL,
  `description` varchar NOT NULL,
  `state` varchar NOT NULL,
  `borrower` varchar NULL,
  `due_time` datetime NULL,
  `request_id` varchar NULL,
  `create_time` datetime NOT NULL,
  `update_time` datetime NOT NULL,
  `delete_time` datetime NULL,
  `etag` varchar NOT NULL,
  PRIMARY KEY (`shelf_id`, `book_id`),
  CONSTRAINT `0` FOREIGN KEY (`shelf_id`) REFERENCES `shelves` (`shelf_id`) ON UPDATE NO ACTION ON DELETE NO ACTION
);
-- Create index "books_request_id" to table: "books"
CREATE UNIQUE INDEX `books_request_id` ON `books` (`request_id`);
-- Create index "ix_books_author" to table: "books"
CREATE INDEX `ix_books_author` ON `books` (`author`);

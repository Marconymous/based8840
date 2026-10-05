// Only `atlas migrate validate` runs here (based8840 verify --full --atlas-env dev).
// migrations/20261005000001_add_note.sql was added without `atlas migrate hash`, so
// atlas.sum no longer matches the directory.
env "dev" {
  // Scratch database Atlas replays the migrations on; in-memory, nothing to install.
  dev = "sqlite://dev?mode=memory"
  migration {
    dir = "file://migrations"
  }
}

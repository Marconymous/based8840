// Desired schema = SQLModel metadata, printed as SQLite DDL by app.storage.db.schema.
data "external_schema" "sqlmodel" {
  program = ["uv", "run", "--quiet", "python", "-m", "app.storage.db.schema"]
}

env "dev" {
  src = data.external_schema.sqlmodel.url
  url = "sqlite://library.db"
  // Scratch database Atlas uses to compute diffs; in-memory, nothing to install.
  dev = "sqlite://dev?mode=memory"
  migration {
    dir = "file://migrations"
  }
  format {
    migrate {
      diff = "{{ sql . \"  \" }}"
    }
  }
}

-- Create FTS virtual table for items based on the 'name' field.
CREATE VIRTUAL TABLE IF NOT EXISTS items_fts 
USING fts5(name, content='item', content_rowid='id');

-- Populate items_fts with existing data.
INSERT INTO items_fts(rowid, name)
    SELECT id, name FROM item;

-- Trigger: After insert, add new row to items_fts.
CREATE TRIGGER IF NOT EXISTS item_ai AFTER INSERT ON item BEGIN
  INSERT INTO items_fts(rowid, name) VALUES (new.id, new.name);
END;

-- Trigger: After delete, remove row from items_fts.
CREATE TRIGGER IF NOT EXISTS item_ad AFTER DELETE ON item BEGIN
  DELETE FROM items_fts WHERE rowid=old.id;
END;

-- Trigger: After update, update row in items_fts.
CREATE TRIGGER IF NOT EXISTS item_au AFTER UPDATE ON item BEGIN
  UPDATE items_fts SET name = new.name WHERE rowid = old.id;
END;

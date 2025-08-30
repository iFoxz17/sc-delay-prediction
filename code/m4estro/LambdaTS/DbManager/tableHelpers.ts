import {Knex} from 'knex';

/**
 * Adds timestamp fields to a table.
 * The timestamps will include created_at and updated_at fields.
 * @param table - The Knex table builder.
 */
export const addTimestamps = (table: Knex.CreateTableBuilder):void => {
    table.timestamps(true, true);
}

/**
 * Adds a primary key field named 'id' to the table.
 * @param table - The Knex table builder.
 */
export const addPrimaryKey = (table: Knex.CreateTableBuilder): void => {
    table.increments('id').primary();
}


/**
 * Adds base fields to a table, including a primary key and timestamps.
 * @param table - The Knex table builder.
 */
export const addBaseFields = (table: Knex.CreateTableBuilder): void => {
    addPrimaryKey(table);
    addTimestamps(table);
}
/*

    * Adds a foreign key constraint to a table.
    * @param table - The Knex table builder.
    * @param columnName - The name of the column to add the foreign key to.
    * @param referencedTable - The name of the table being referenced.
    * @param referencedColumn - The name of the column in the referenced table (default is 'id').
    * @param nullable - Whether the foreign key column can be null (default is false).
    * @param columnType - The type of the foreign key column, either 'integer' or 'string' (default is 'integer').
*/
export const addForeignKey = (
  table: Knex.CreateTableBuilder,
  columnName: string,
  referencedTable: string,
  referencedColumn: string = 'id',
  nullable: boolean = false,
  columnType: 'integer' | 'string' = 'integer',
  columnLength: number = 0,
  hasDefault: boolean = false,
  defaultValue: any = null
): void => {
  let column: Knex.ColumnBuilder;

  if (columnType === 'string') {
    if (columnLength > 0) {
      column = table.string(columnName, columnLength);
    } else {
      column = table.string(columnName);
    }
  } else {
    column = table.integer(columnName).unsigned();
  }

  if (!nullable) {
    column.notNullable();
  }
  if (hasDefault) {
    column.defaultTo(defaultValue);
  }

  column.references(referencedColumn).inTable(referencedTable).onDelete('RESTRICT').onUpdate('CASCADE');
  table.index([columnName]);
};



/**
 * Adds a composite index to the table.
 * @param table - The Knex table builder.
 * @param columns - An array of column names to include in the composite index.
 * @param indexName - Optional name for the index. If not provided, a default name will be generated.
 */

export const addCompositeIndex = (
  table: Knex.CreateTableBuilder,
  columns: string[],
  indexName?: string
): void => {
  const name = indexName || `idx_${columns.join('_')}`;
  table.index(columns, name);
};


/**
 * Adds statistical fields to the table.
 * These fields are typically used for statistical analysis.
 * @param table - The Knex table builder.
 */
export const addSampleFields = (table: Knex.CreateTableBuilder): void => {
  table.decimal('median', 12, 6).notNullable();     // Median of the sample
  table.decimal('mean', 12, 6).notNullable();       // Mean of the sample
  table.decimal('std_dev', 12, 6).notNullable();    // Standard deviation of the sample
  table.integer('n').unsigned().notNullable();      // Number of observations in the sample
};


/**
 * Adds fields for the gamma distribution.
 * These fields are typically used in statistical modeling.
 * @param table - The Knex table builder.
 */
export const addGammaFields = (table: Knex.CreateTableBuilder): void => {
  table.decimal('shape', 12, 6).notNullable();
  table.decimal('loc', 12, 6).notNullable();
  table.decimal('scale', 12, 6).notNullable();
  table.decimal('skewness', 12, 6).notNullable();
  table.decimal('kurtosis', 12, 6).notNullable();
  table.decimal('mean', 12, 6).notNullable();     // Mean of the original sample
  table.decimal('std_dev', 12, 6).notNullable();  // Standard deviation of the original sample
  table.integer('n').unsigned().notNullable();    // Number of observations of the sample
};


/**
 * Adds location fields to the table.
 * These fields are typically used to store geographical coordinates.
 * @param table - The Knex table builder.
 */
export const addLocationFields = (table: Knex.CreateTableBuilder): void => {
  table.decimal('latitude', 9, 7).notNullable();
  table.decimal('longitude', 10, 7).notNullable();
};


/**
 * Adds a timestamp field with timezone support to the table.
 * @param table - The Knex table builder.
 * @param columnName - The name of the timestamp column.
 * @param nullable - Whether the timestamp column can be null (default is true).
 */
export const addTimestampWithTz = (
  table: Knex.CreateTableBuilder,
  columnName: string,
  nullable: boolean = false
): void => {
  const column = table.timestamp(columnName, { useTz: true });
  if (nullable) {
    column.nullable();
  } else {
    column.notNullable();
  }
};
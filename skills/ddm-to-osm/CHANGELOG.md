# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-03-03

### Added
- Initial release
- DDM XML parser supporting Datablau LDM format
- OSM YAML generator with 4-layer architecture
- Automatic entity, attribute, and relationship extraction
- Semantic type inference (identifier, name, email, phone, currency, etc.)
- Join graph generation from foreign key relationships
- Basic KPI generation for each entity
- Governance layer with basic rules and policies
- Cross-platform support (Windows, Linux, macOS)
- Comprehensive documentation
- Example DDM file and test script

### Features
- Parse EntityComposite, EntityAttribute, EntityKeyGroup
- Parse RelationshipRelational with KeyGroup resolution
- Generate Ontology Layer (entities, attributes, relations)
- Generate Semantic Model Layer (dimensions, measures, joins)
- Generate Join Graph (nodes and edges)
- Generate KPI Layer (basic count KPIs)
- Generate Governance Layer (rules and policies)
- Smart data type mapping (DDM physical → OSM semantic)
- Chinese label support
- UTF-8 encoding handling for Windows console

### Supported
- Datablau LDM DDM format
- MySQL, PostgreSQL, and other relational databases
- One-to-many, many-to-one relationships
- Primary keys, foreign keys, and indexes

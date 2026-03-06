# Changelog

All notable changes to this project will be documented in this file.

## [1.3.0-p2] - 2026-03-06

### Added
- `convert.py` enhancements:
  - `--report` option to generate markdown generation report
  - meta injection of `model_version` and `source_fingerprint`
- New script: `diff_osm.py`
  - compare old/new OSM files
  - output summary/details in markdown/json
- New script: `make_release_artifacts.py`
  - one-shot pipeline for OSM/report/lint/curated/diff/manifest
- Extended regression tests in `test.py` for P2 workflows:
  - convert report generation
  - meta fingerprint/version checks
  - diff report generation
  - release manifest validation

### Changed
- Updated README/SKILL docs for P2 workflows and commands
- Improved cross-script Windows stream wrapping safety to avoid closed stream issues

### Fixed
- Fixed repeated stdout/stderr wrapping issue under Windows in multi-script pipeline
- Ensured release pipeline outputs stable `manifest.json` summary fields


### Added
- Ontology layer additions:
  - `constraints` (auto-generated + profile override)
  - `enums` (auto-generated + profile override)
- Semantic model additions:
  - `filters` (auto templates + profile merge)
  - join override via profile (`expression`, `temporal_validity`)
- KPI normalization pipeline:
  - normalized `time` shape
  - default `constraints` and `dependencies`
- New linter script: `lint_osm.py`
  - reference consistency checks
  - KPI structural checks
  - governance/kpi consistency checks
- Extended regression tests in `test.py` for P1 structures and profile overrides

### Changed
- `osm_generator.py` version updated to `1.2.0-p1`
- Expression-style joins now clean legacy key fields (`local_key`, `foreign_key`, etc.)
- Curated KPI pack behavior updated:
  - recursively include KPI dependencies
  - synchronize `governance.policies.role_permissions.*.allowed_kpis`

### Fixed
- Eliminated curated KPI dangling dependencies (formula/period_compare)
- Fixed governance `allowed_kpis` drift after KPI curation
- Improved Windows output wrapping safety in `lint_osm.py`

## [1.1.0-p0] - 2026-03-06

### Added
- Parser support for composite foreign keys (multi-column FK)
- Parser support for unique keys extraction
- FK metadata extraction: `on_delete` / `on_update`
- OSM output `meta` section (`schema_version`, `generator_version`, `generated_at`, `source`)
- CLI options:
  - `--kpi-mode basic|advanced`
  - `--profile <yaml>`
- Example profile file: `profile.example.yaml`
- Enhanced regression tests in `test.py` (parser/generator/golden checks)

### Changed
- Refactored cardinality mapping in parser
- Improved semantic type inference with boundary-aware regex
- Improved relation inverse naming (`city -> cities`, `address -> addresses`)
- Unified KPI time structure:
  - `dimension`
  - `default_grain`
  - `allowed_grains`
  - `window`
- Join condition generation now supports both single-key and composite-key forms

### Fixed
- Reduced false-positive semantic type inference (e.g. avoid `country -> count`)
- Fixed inconsistent relation inverse plural forms

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

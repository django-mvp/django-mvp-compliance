# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `Document` and `Version` models for versioned legal text: a document holds
  a lasting name, and each version holds the Markdown wording written for
  it. A version starts as a draft, and publishing renders it to HTML,
  makes it the version in force, and moves the previous one to superseded.
  A published version's wording can never change again.
- Rendering depends on `markdown`, which turns the authored wording into
  HTML, and `nh3`, which sanitises that HTML against an explicit allow list
  before it is stored. The renderer used is configurable with one setting,
  `MVP_COMPLIANCE_RENDERER`, a dotted path to a renderer class, defaulting
  to the one this package ships.

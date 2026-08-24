# Changelog

All notable changes to ZeroGravity will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Full catalog screening support for 30,070+ objects (2026-02-10)
- Debris-on-payload conjunction screening capability
- Screening now includes active satellites, rocket bodies, debris, and unknown objects
- Daily screening capability for operational satellite safety
- Enhanced data sources documentation covering CelesTrak full catalog and SATCAT classification

### Changed
- Expanded screening from 14,368 active satellites to full 30,070 object catalog
- Updated performance benchmarks: ~15-20 seconds for full catalog screening on Jetson Orin Nano
- Improved orbital shell prefilter to handle larger catalog (~800 candidates vs ~500 previously)
- Updated batch SGP4 propagation benchmarks for 30K+ objects (~40ms)

### Performance
- Full catalog propagation: ~40ms for 30,070 objects
- Complete conjunction screening (7 days): ~15-20 seconds on ARM hardware (Jetson Orin Nano)
- Scales linearly with catalog size while maintaining sub-20-second screening times

---

## Prior Releases

See git history for earlier changes. This changelog begins with the full catalog expansion.

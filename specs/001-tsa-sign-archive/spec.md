# Feature Specification: TSA Sign & Archive CLI

**Feature Branch**: `001-tsa-sign-archive`

**Created**: 2026-07-29

**Status**: Draft

**Input**: User description: "I want to build a CLI tool to sign with a set of TSA servers (multiple per run for extra security) and archive as a ZIP the contents of a directory. The idea is to generate a report that includes the signature of each file + metadata (SHA256, MD5, and per file specifics, for example in the videos the duration, frames, fps, bitrate, resolution, encoder etc. For images the format, resolution, etc). The archive is ITERATIVE, new contents will be added to the archive, so i need the report to include the original time signatures instead of the new ones created during runtime. If there are missing files or metadata changes, the run must also output an extra file that reports these changes (as maybe a file has been corrupted or modified by an external program). NOTE: The TSA servers must be configurable, a default list will be given. Along with the report + output log there should be a timestamped archive (ZIP) of the folder that will keep the integrity of the files that are reflected in the report. I need this tool to have legal validity IN SPAIN."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - First-Time Archive Creation (Priority: P1)

A user has a directory of digital evidence (videos, images, documents) that needs to be timestamped and archived with legal validity under Spanish law. They run the CLI tool, pointing it at the directory. The tool computes cryptographic hashes (SHA-256, MD5) for every file, extracts file-specific metadata (video duration/frames/fps/bitrate/resolution/encoder, image format/resolution, document page count/author), sends each file's hash to multiple TSA servers (at least 2) to obtain RFC 3161 timestamps, creates a timestamped ZIP archive, and generates a signed report containing all signatures, hashes, and metadata.

**Why this priority**: This is the core value proposition — without initial archiving, no other workflows (iterative updates, tamper detection) are possible.

**Independent Test**: Can be fully tested by running the tool against any directory of mixed media files and verifying that a ZIP archive and a signed report are produced with correct hashes, timestamps from multiple TSA servers, and accurate file metadata.

**Acceptance Scenarios**:

1. **Given** a directory with 10 files (images, videos, text documents), **When** the user runs the tool for the first time, **Then** a timestamped ZIP archive is created containing all files, a signed PDF/A report is generated listing each file with its SHA-256, MD5, file-specific metadata, and TSA timestamps from all configured servers, and a run log is produced.
2. **Given** a TSA server is unreachable, **When** the tool attempts to obtain a timestamp, **Then** the tool retries according to configured retry policy and logs the failure; the run succeeds as long as at least one TSA server responds.
3. **Given** a file type with no specialized metadata extractor (e.g., unknown binary format), **When** the tool processes it, **Then** basic metadata (filename, size, SHA-256, MD5) is still recorded and the report notes "no specialized metadata available" for that file.

---

### User Story 2 - Iterative Archive Update & Change Detection (Priority: P2)

A user has previously archived a directory. Over time, new files are added, some files may have been modified externally, and some may have been deleted. The user runs the tool again on the same directory. The tool compares the current state against the last archive report, identifies new files (which get timestamped and added to the archive), detects modified files (hash mismatch) and missing files, and generates a delta change report documenting all differences.

**Why this priority**: Iterative archiving is the second most critical feature — users need to maintain a growing archive over time, and tamper/change detection is essential for legal chain of custody.

**Independent Test**: Create an initial archive, then add a new file, modify an existing file's content, and delete another file. Run the tool again and verify: the new file is timestamped and added to the ZIP, the modified and missing files are flagged in the delta report, and all unchanged files retain their original timestamps in the report.

**Acceptance Scenarios**:

1. **Given** a previously archived directory where 2 new files were added, 1 existing file was modified, and 1 file was deleted, **When** the tool runs again, **Then** the 2 new files are timestamped and added to the archive, the modified file and deleted file are flagged in a delta change report with before/after hashes and metadata, and the report preserves original timestamps for all unchanged files.
2. **Given** a previously archived directory where no files have changed, **When** the tool runs again, **Then** the tool reports "no changes detected," no new timestamps are requested, and the existing archive and report remain valid.
3. **Given** the previous archive report is missing or corrupted, **When** the tool runs, **Then** the tool warns the user that baseline data is unavailable and treats the run as a first-time archive creation.

---

### User Story 3 - TSA Server Configuration (Priority: P2)

A user needs to configure which TSA servers are used for timestamping. A default list of qualified EU TSA providers is included out of the box. The user can view, add, remove, or reorder TSA servers via a configuration file.

**Why this priority**: Configurable TSA servers are essential for the multi-TSA signing requirement and for selecting providers with legal recognition in Spain/EU. Without this, users cannot adapt to specific compliance or organizational requirements.

**Independent Test**: Edit the configuration file to add a custom TSA server URL, remove the default ones, and run the tool — verify it uses only the configured servers.

**Acceptance Scenarios**:

1. **Given** the tool is installed with default configuration, **When** the user runs it without any custom TSA configuration, **Then** the default list of qualified EU TSA providers is used.
2. **Given** the user edits the TSA configuration file to add a custom server and remove a default one, **When** the tool runs, **Then** it queries only the servers in the user's configuration.
3. **Given** a configured TSA server URL is malformed, **When** the tool starts, **Then** it validates the configuration and reports a clear error before any processing begins.

---

### User Story 4 - Report and Archive Verification (Priority: P3)

A user or a third-party verifier (e.g., a legal professional, auditor, or court) needs to verify the integrity and authenticity of an archived report and its associated ZIP. The tool provides a verification subcommand that checks the report's signature, verifies TSA timestamps against the TSA certificates, and validates that file hashes in the report match the actual files in the ZIP archive.

**Why this priority**: Verification is essential for the tool's legal validity claims — a signed archive is only useful if it can be independently verified by third parties.

**Independent Test**: Run the verification command on a previously created archive and report; verify it confirms all signatures are valid, hashes match, and timestamps are authentic.

**Acceptance Scenarios**:

1. **Given** a valid signed report and ZIP archive produced by the tool, **When** the verification command is run, **Then** it confirms all file hashes match, all TSA timestamps are cryptographically valid, and the report's own signature is intact.
2. **Given** a ZIP archive where one file's content has been tampered with, **When** the verification command is run, **Then** it reports hash mismatch for that specific file with details.
3. **Given** a report signed with an expired TSA certificate, **When** the verification command is run, **Then** it reports that the timestamp uses an expired certificate but notes the timestamp was valid at the time of signing (if the signing time predates expiry).

---

### User Story 5 - Legal Compliance for Spain / EU eIDAS (Priority: P1)

The tool must produce outputs that are admissible as evidence in Spanish legal proceedings. This means the timestamps must come from qualified TSA providers recognized under EU eIDAS Regulation (910/2014), the report must be in a format suitable for long-term legal preservation (PDF/A), and both the report and archive must be cryptographically signed to establish an unbroken chain of custody.

**Why this priority**: The user explicitly requires legal validity in Spain. Without meeting eIDAS standards, the tool fails its primary purpose regardless of other functionality.

**Independent Test**: An independent legal/technical auditor can verify that timestamps are obtained from qualified eIDAS TSA providers, the report format conforms to PDF/A-3 for long-term preservation, and the cryptographic signatures follow recognized standards (X.509, RFC 3161, CAdES/PAdES).

**Acceptance Scenarios**:

1. **Given** the tool is configured with the default TSA server list, **When** it obtains timestamps, **Then** all TSA servers in the list are qualified providers under EU eIDAS (listed in the EU Trusted List — EUTL).
2. **Given** the tool produces a report, **When** the report is inspected, **Then** it conforms to PDF/A-3 format with embedded signature (PAdES) suitable for long-term archival.
3. **Given** a legal proceeding requires evidence of file integrity at a specific point in time, **When** the signed report and timestamped archive are presented, **Then** the timestamps from multiple independent qualified TSAs provide corroborating proof of file existence and integrity at the timestamped moment.

---

### Edge Cases

- **Empty directory**: What happens when the target directory contains no files? The tool should produce a valid report stating "no files to archive" and exit cleanly.
- **Very large files**: How does the tool handle files exceeding available memory (e.g., 10GB+ video files)? Hashing and archiving must use streaming to avoid memory exhaustion.
- **Files locked by other processes**: If a file cannot be read (permission denied, locked), the tool must log the error per file and continue processing remaining files, listing inaccessible files in the report.
- **Network interruption during TSA signing**: If the network fails mid-signing, the tool must retry with exponential backoff for each TSA server independently, and report which servers succeeded vs. failed.
- **TSA servers return conflicting timestamps**: If two TSA servers return timestamps with significant clock skew (e.g., >5 seconds), the tool should flag this in the report but still record both timestamps.
- **Archive ZIP grows very large over time**: With iterative updates, the ZIP archive may become very large. The tool should warn if the ZIP exceeds a configurable size threshold.
- **Unicode/special characters in filenames**: Filenames with non-ASCII characters must be correctly handled and preserved in the ZIP archive and report.
- **Symbolic links and directory structures**: The tool must define a clear policy for symlinks (follow, store as link, or skip) and preserve directory structure in the archive.
- **Concurrent runs**: What happens if two instances of the tool run against the same directory simultaneously? The tool must use file locking to prevent corruption.

## Requirements *(mandatory)*

### Functional Requirements

#### Signing & Hashing

- **FR-001**: System MUST compute SHA-256 and MD5 cryptographic hashes for every file in the target directory.
- **FR-002**: System MUST send each file's hash to all configured TSA servers and obtain RFC 3161 timestamp response tokens.
- **FR-003**: System MUST query a minimum of 2 TSA servers per file to provide corroborating timestamps.
- **FR-004**: System MUST store the raw TSA timestamp tokens (RFC 3161 TimeStampToken) for each file, enabling independent verification by third parties without the tool.
- **FR-005**: System MUST use at least one qualified TSA provider from the EU Trusted List (EUTL) by default to ensure legal validity in Spain under eIDAS.

#### Archiving

- **FR-006**: System MUST create a timestamped ZIP archive containing all files from the target directory, preserving directory structure and original file modification times.
- **FR-007**: System MUST support iterative archiving: on subsequent runs, only new files are added to the existing ZIP archive; unchanged files are not duplicated.
- **FR-008**: System MUST embed or bundle timestamp tokens with the archive so that verification can be performed without access to the original TSA servers.

#### Reporting

- **FR-009**: System MUST generate a report containing, for each file: filename, relative path, file size, SHA-256 hash, MD5 hash, TSA timestamps (one per server with server identity and signing time), and file-type-specific metadata. The report MUST also include the archive-level metadata: the archive ZIP file's own SHA-256 and MD5 hashes, archive file size, total file count, and archive creation timestamp.
- **FR-010**: System MUST generate the report in PDF/A-3 format for long-term legal preservation.
- **FR-011**: System MUST extract video-specific metadata using ffprobe (bundled with FFmpeg): duration, frame count, frames per second (FPS), bitrate, resolution (width x height), video codec/encoder, audio codec (if present).
- **FR-012**: System MUST extract image-specific metadata using ffprobe (bundled with FFmpeg): image format, resolution (width x height), color mode, bits per channel, pixel format, EXIF data (where available).
- **FR-011a**: System MUST check for FFmpeg availability at startup; if ffprobe is not found on the system PATH, the tool MUST error and exit with a clear message unless the `--skip-ffmpeg-meta` flag is passed, which allows the run to proceed with basic metadata only (size, hashes, filename).
- **FR-013**: System MUST extract document-specific metadata: page count, author, creation date (where embedded), format/type.
- **FR-014**: System MUST cryptographically sign the report (PAdES — PDF Advanced Electronic Signature) using a digital certificate, establishing authorship and integrity.
- **FR-015**: System MUST sign the ZIP archive with a detached cryptographic signature (CAdES or equivalent), establishing chain of custody.

#### Change Detection

- **FR-016**: System MUST detect, on iterative runs, any file that is present in the previous archive report but missing from the current directory.
- **FR-017**: System MUST detect, on iterative runs, any file whose SHA-256 hash differs from the hash recorded in the previous archive report (indicating content modification).
- **FR-018**: System MUST detect, on iterative runs, any file whose metadata differs from the metadata recorded in the previous report (even if the hash is unchanged).
- **FR-019**: System MUST generate a separate delta change report (in PDF/A-3 format) that lists all detected changes: added files, removed files, modified files (with before/after hashes and metadata), and files with metadata-only changes.
- **FR-020**: System MUST preserve and carry forward original timestamps for files that have not changed between iterations; the iterative report must reference the original signing time, not the current run time.

#### Configuration

- **FR-021**: System MUST store all run state and configuration in a `.signed_archive/` folder located inside the `--input` target directory.
- **FR-022**: System MUST use a YAML configuration file (`.signed_archive/config.yml`) for TSA server URLs and runtime options. The tool MUST generate a default `config.yml` on first run if none exists.
- **FR-023**: System MUST validate TSA server URLs at startup and reject malformed URLs with a clear error message.
- **FR-024**: System MUST allow configuration of retry policy (max retries, backoff strategy, timeout) for TSA requests.
- **FR-021a**: System MUST preserve the previous run's file hashes and metadata in `.signed_archive/state.json` for comparison on iterative runs. Comparison MUST be based on hash values, not just filenames.
- **FR-022a**: The default TSA server list MUST include the following three qualified Spanish TSA providers: ACCV (Comunidad Valenciana — http://tss.accv.es:8318/tsa), CATCert (Catalunya — http://psis.catcert.net/psis/catcert/tsp), and IZENPE (País Vasco — http://tsa.izenpe.com).

#### Verification

- **FR-025**: System MUST provide a verification command that validates the integrity of a signed report and its associated ZIP archive.
- **FR-026**: Verification MUST check that every file hash in the report matches the corresponding file in the ZIP archive.
- **FR-027**: Verification MUST validate all TSA timestamps cryptographically (signature verification of each RFC 3161 token).
- **FR-028**: Verification MUST validate the report's own digital signature (PAdES signature integrity).
- **FR-029**: Verification MUST produce a human-readable verification report indicating pass/fail per file and per TSA timestamp.

#### Output & Logging

- **FR-030**: System MUST produce a timestamped run log for every execution, recording all operations, TSA interactions, errors, and warnings.
- **FR-031**: System MUST name output files with an ISO 8601 timestamp to ensure uniqueness and sortability (e.g., `archive_20260729T203000Z.zip`).

#### Robustness

- **FR-032**: System MUST continue processing remaining files when an individual file cannot be read, logging the error and listing the file as "skipped" in the report.
- **FR-033**: System MUST use streaming I/O for hashing and archiving large files to avoid memory exhaustion.
- **FR-034**: System MUST handle filenames with Unicode characters correctly on all supported platforms.
- **FR-035**: System MUST use file locking to prevent corruption when multiple instances run against the same directory.

### Key Entities

- **ArchiveRun**: Represents a single execution of the tool. Contains: run timestamp, target directory path, configuration used, list of TSA servers queried, outcome (success/partial/failure).
- **FileRecord**: Represents a file processed during a run. Contains: file path, size, SHA-256 hash, MD5 hash, file-type-specific metadata (video/image/document), processing status (processed/skipped/error).
- **TimestampSignature**: Represents a TSA timestamp obtained for a specific file. Contains: TSA server URL, signing time (UTC), raw RFC 3161 token, certificate chain, verification status.
- **DeltaChange**: Represents a detected change between two runs. Contains: change type (added/removed/modified/metadata-changed), file path, before-state data (hash, metadata), after-state data (hash, metadata).
- **TSAConfiguration**: Represents the list of configured TSA servers. Contains: ordered list of server URLs, retry policy parameters, timeout settings.
- **Report**: Represents the generated archive report. Contains: list of FileRecords with associated TimestampSignatures, report signature, report format version, run metadata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user can archive a directory of up to 1,000 files and receive a complete signed report within 5 minutes (assuming responsive TSA servers and typical file sizes under 100MB total).
- **SC-002**: The iterative update process correctly identifies 100% of added, removed, and modified files when comparing against a previous archive report.
- **SC-003**: A third-party verifier (without access to the tool's private keys) can independently validate the report signature, all TSA timestamps, and file integrity using only the report, ZIP archive, and public certificates.
- **SC-004**: The tool produces a valid timestamp from at least 2 independent TSA servers for every file processed, providing corroborating evidence.
- **SC-005**: The generated report conforms to PDF/A-3 specification as validated by a standards-compliant PDF/A conformance checker, ensuring long-term (10+ years) legal admissibility.
- **SC-006**: 95% of file-specific metadata (video duration/fps/resolution/codec, image format/resolution, document page count) is correctly extracted for common file formats (MP4, MOV, AVI, JPEG, PNG, TIFF, PDF, DOCX).
- **SC-007**: The tool handles a 10GB single file without exceeding 512MB of memory (streaming I/O for hashing and archiving).
- **SC-008**: A user can configure a custom TSA server list and run the tool with less than 2 minutes of configuration effort.

## Assumptions

1. **Report Format**: PDF/A-3 is chosen as the report format because it is the ISO standard (ISO 19005-3) for long-term electronic document preservation and is recognized in EU/Spanish legal contexts. Markdown was considered but rejected as it lacks embedded signatures and long-term archival properties.

2. **Report Signing**: The report will be digitally signed (PAdES baseline) to establish authorship and integrity. This is necessary for legal chain of custody — an unsigned report could be challenged as self-serving.

3. **Archive Signing**: The ZIP archive will have a detached cryptographic signature (CAdES format) to prove the archive was produced by the tool and has not been tampered with. This completes the chain of custody: signed report references signed archive.

4. **Digital Certificate for Signing**: The user must provide a digital certificate (X.509) for signing the report and archive. The tool will use this certificate; it does not generate certificates. For legal validity in Spain, the certificate should be issued by a qualified trust service provider recognized under eIDAS (e.g., FNMT — Fábrica Nacional de Moneda y Timbre, or other EU qualified providers).

5. **TSA Servers**: The three default TSA servers are qualified Spanish providers under eIDAS: ACCV (Comunidad Valenciana — http://tss.accv.es:8318/tsa), CATCert (Catalunya — http://psis.catcert.net/psis/catcert/tsp), and IZENPE (País Vasco — http://tsa.izenpe.com). All use RFC 3161 over HTTP. The tool queries all three for every file to provide triple corroboration.

6. **Metadata Extraction via FFmpeg**: Video and image metadata extraction relies on ffprobe (bundled with FFmpeg). FFmpeg must be installed and available on the system PATH. If unavailable, the `--skip-ffmpeg-meta` flag skips deep metadata extraction and records only basic metadata (size, hashes, filename). The tool errors by default if ffmpeg is not found, since video/image metadata is critical for the tool's legal validity purpose.

7. **Run State Storage**: Iterative run metadata (file hashes, TSA timestamps, metadata snapshots) is stored in `.signed_archive/state.json` inside the input directory. The configuration is stored in `.signed_archive/config.yml`. Both files are regenerated or updated on each run to reflect the latest state for the next comparison.

8. **ZIP Format**: The ZIP64 extension will be used if files or archive exceed 4GB. The archive is created in the output directory with an ISO 8601 timestamp in the filename (e.g., `archive_20260729T203000Z.zip`). The archive's own hash is computed after creation and included in the report for self-referential integrity verification.

9. **Platform Support**: The CLI tool targets Windows, macOS, and Linux. Windows is the initial target given the development environment.

10. **Single Directory Scope**: Each run targets one directory. Nested subdirectories are processed recursively. Symlinks are followed by default with a configurable option to skip them.

11. **TSA Timestamp Clock Skew**: Timestamps from different TSA servers may differ by a few seconds due to clock skew. The tool accepts timestamps from each server independently without attempting to reconcile clock differences, but flags skews exceeding 5 seconds in the log.

12. **Legal Disclaimer**: While the tool incorporates technical measures supporting legal validity, the user is responsible for ensuring their specific use case meets legal requirements (e.g., using a qualified certificate, retaining the signed report and archive, following procedural requirements under Spanish Law 6/2020 regulating trust services).

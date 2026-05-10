# mts-ontology.md — Masters Tuition Services Domain Ontology

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active

---

## 1. Purpose

This ontology defines the foundational concepts, relationships, and constraints
of the MTS domain.

It is the **semantic backbone** of the MTS system. All agents, specs, workflows,
and code must use concepts consistently with how they are defined here.

When terminology is unclear, consult the ontology first.
When the ontology is incomplete, extend it — do not invent ad hoc.

---

## 2. Core Concept Hierarchy

```text
MTS Organization
 ├── serves → Student (Grades 2–10)
 ├── employs → Teacher
 ├── operates → Venue
 ├── runs → Batch (per grade/subject)
 │     └── contains → Session (per week)
 ├── teaches → Subject (Math | ELA | IT | Sciences)
 ├── follows → Curriculum (NC Common Core | AIG)
 └── produces → Educational Material
       ├── Worksheet
       ├── Answer Key
       ├── Lesson Plan
       └── Source PDF (input)
```

---

## 3. Entity Definitions

---

### 3.1 Student

**Definition:**
A learner in Grades 2–10 attending MTS sessions.

**Attributes:**
| Attribute | Type | Notes |
|-----------|------|-------|
| grade | integer | 2–10 |
| batch | Batch | which group session they attend |
| subjects | list[Subject] | enrolled subjects |

**Constraints:**
* Content generated for a student must match their declared grade level.
* No PII about a student is stored in system artifacts.

**Relationships:**
```text
Student
 ├── attends → Batch
 ├── receives → Worksheet
 └── aligned to → Grade
```

---

### 3.2 Teacher

**Definition:**
An MTS instructor who delivers sessions and is the primary consumer of
system-generated content.

**Roles:**
| Role | Description |
|------|-------------|
| Main Teacher | Leads instruction; defines pedagogical direction |
| Support Teacher | Assists; provides secondary instruction |

**Relationships:**
```text
Teacher
 ├── leads → Batch
 ├── receives → Worksheet, Answer Key, Lesson Plan
 └── provides → Source PDF (input to pipeline)
```

---

### 3.3 Grade

**Definition:**
The US school grade level declaring the cognitive maturity and curriculum
stage of a student.

**Valid Values:** 2, 3, 4, 5, 6, 7, 8, 9, 10

**Bands:**
| Band | Grades | Mode |
|------|--------|------|
| Elementary | 2–4 (5 on demand) | Math & ELA |
| Middle & High School | 8–10 (7 on demand) | Math, ELA, IT, Sciences |

**Constraints:**
* All content MUST be assessed against grade-level cognitive load expectations.
* Grade is required for any content generation task.

---

### 3.4 Subject

**Definition:**
An academic discipline taught at MTS.

**Valid Values:**
| Subject | Mode | Grades |
|---------|------|--------|
| Math | Instructional | 2–10 |
| ELA | Instructional | 2–10 |
| IT | Guidance | 8–10 |
| Sciences | Guidance | 8–10 |

**Instructional** = MTS takes full instructional responsibility.
**Guidance** = MTS provides support and direction but does not own full curriculum.

---

### 3.5 Batch

**Definition:**
A scheduled group of students at the same grade level, attending on a fixed
recurring weekly slot.

**Attributes:**
| Attribute | Type | Notes |
|-----------|------|-------|
| grade | Grade | grade served |
| subject | list[Subject] | subjects in session |
| venue | Venue | location |
| day | string | day of week |
| time | string | start time |
| duration | integer | minutes |

**Constraints:**
* One batch per grade per session time.
* Capacity is intentionally small (a few slots per grade).

---

### 3.6 Session

**Definition:**
A single occurrence of a Batch. One session per week per batch.

**Relationships:**
```text
Session
 ├── instance of → Batch
 ├── uses → Worksheet
 └── uses → Lesson Plan
```

---

### 3.7 Source PDF

**Definition:**
A teacher-provided PDF containing source worksheet content.
The primary input to transformation pipelines.

**Attributes:**
| Attribute | Type | Notes |
|-----------|------|-------|
| grade | Grade | declared grade level |
| subject | Subject | declared subject |
| file_path | string | local path |
| page_count | integer | total pages |

**Constraints:**
* Source PDFs are read-only. Pipelines never modify the source.
* Source PDFs are confidential teaching materials.
* Content from source PDFs is transformed, never invented beyond it.

---

### 3.8 Block

**Definition:**
A discrete question region extracted from a source PDF page.
The atomic content unit in the `compact_source` pipeline.

**Attributes:**
| Attribute | Type | Notes |
|-----------|------|-------|
| page_index | integer | 0-indexed source page |
| bbox | tuple[float] | bounding box (x0, y0, x1, y1) |
| image | bytes | rasterized block image |
| block_index | integer | position on page |

**Relationships:**
```text
Block
 ├── extracted from → Source PDF page
 └── packed into → Output PDF
```

**Constraints:**
* Blocks are never modified after extraction — only repacked.
* A suspiciously low block count (< 3 total, or < 0.5 per page) triggers WARNING.

---

### 3.9 Worksheet

**Definition:**
A student-facing document containing practice problems for a declared
grade level and subject.

**Attributes:**
| Attribute | Type | Notes |
|-----------|------|-------|
| grade | Grade | declared grade level |
| subject | Subject | declared subject |
| problem_count | integer | number of problems |
| format | string | compact | full | two-column |
| source | Source PDF \| None | origin material if sourced |

**Relationships:**
```text
Worksheet
 ├── generated from → Source PDF (if applicable)
 ├── evaluated by → QA Agent
 ├── accompanied by → Answer Key
 └── delivered to → Teacher → Student
```

**Quality Constraints:**
* Grade alignment required
* No incorrect answers
* No invented content (when source-grounded)
* QA PASS required before delivery

---

### 3.10 Answer Key

**Definition:**
A teacher-facing companion to a Worksheet showing correct answers
and, for math, step-by-step solutions.

**Constraints:**
* Never delivered directly to students.
* Must match the corresponding Worksheet exactly.
* Mathematical answers show working, not just final values.

---

### 3.11 Curriculum Standard

**Definition:**
The external academic framework defining what students at a given grade
level should know and be able to do.

**Values:**
| Standard | Scope |
|---------|-------|
| NC Common Core | Primary reference for all grades |
| AIG | Academically and Intellectually Gifted track |
| SAT Prep | Implicit target for Grades 9–10 |

**Relationships:**
```text
Curriculum Standard
 ├── governs → Subject content at Grade
 └── referenced by → Worksheet, Lesson Plan quality evaluation
```

---

### 3.12 Pipeline

**Definition:**
An end-to-end sequence of processing stages that transforms an input
into one or more output artifacts.

**Attributes:**
| Attribute | Type | Notes |
|-----------|------|-------|
| feature | string | which feature this pipeline serves |
| stages | list[Stage] | ordered execution sequence |
| artifacts | list[Artifact] | expected outputs |

**Current Pipelines:**
| Pipeline | Feature |
|---------|---------|
| compact_source_math | Compact math source PDF |
| compact_source_reading | Compact reading source PDF |
| math_worksheet_generation_from_source | Generate math worksheet from source |

---

### 3.13 Artifact

**Definition:**
Any file produced by a pipeline run.

**Types:**
| Type | Description |
|------|-------------|
| Output PDF | The final deliverable |
| Run Log | Execution trace |
| Eval Report | Quality evaluation findings |
| Block Images | Intermediate extracted block rasters |
| Failure Log | Diagnostic information on pipeline failure |

**Constraints:**
* Every pipeline run produces at minimum a run log.
* Artifacts are append-only — they are never overwritten by subsequent runs.

---

## 4. Relationship Summary

```text
Teacher
 ├── provides → Source PDF
 ├── receives → Worksheet + Answer Key
 └── leads → Batch

Batch
 ├── grade: Grade
 ├── subject: Subject
 └── venue: Venue

Source PDF → [Pipeline] → Worksheet + Answer Key + Run Log + Eval Report

Student
 ├── attends → Batch
 └── receives → Worksheet (via Teacher)

Curriculum Standard → governs → Worksheet quality ← evaluated by → QA Agent
```

---

## 5. Ontology Governance

* The ontology is versioned.
* New concepts are added here before being used in specs or code.
* Renamed or deprecated concepts are marked as such — existing references updated.
* Ontology changes are recorded in `decisions.md`.

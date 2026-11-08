# Sources to verify (owner: workstream D)

Everything below is a **candidate**, written from general knowledge. **SOURCE TO BE VERIFIED** applies to every row: law number, year, title, current status and URL must be confirmed on the official source before ingestion. No URLs are given on purpose; take them from the official site when you download.

Workflow per document:
1. Find it on the official source.
2. Download the Arabic original and the official English translation (if any) into `kb/raw/<layer>/`.
3. Add one row per language to `kb/sources.csv` and set `verified=true`.
4. Tick the box here.

Priority: ★ = needed for the first 10–15 documents (Phase 2).

## Layer `uae_federal` (primary)
Official sources: the UAE Legislation portal, ministry/regulator sites (TDRA, Ministry of Education, Ministry of Economy, UAE Data Office), and the Official Gazette.

- [ ] ★ Personal data protection: Federal Decree-Law No. 45 of 2021 (PDPL). Also check whether its **executive regulations** have been issued, and their status. *SOURCE TO BE VERIFIED*
- [ ] ★ Child rights: Federal Law No. 3 of 2016 on Child Rights ("Wadeema's Law") and its executive regulations. *SOURCE TO BE VERIFIED*
- [ ] ★ Child digital safety: a dedicated federal decree-law on child digital safety, reportedly issued in 2025. Number, date and effective date unknown. *SOURCE TO BE VERIFIED*
- [ ] ★ Consumer protection: Federal Law No. 15 of 2020 on Consumer Protection and its executive regulations. *SOURCE TO BE VERIFIED*
- [ ] ★ E-commerce: Federal Decree-Law No. 14 of 2023 on trading by modern technological means (e-commerce). *SOURCE TO BE VERIFIED*
- [ ] ★ Cybercrime: Federal Decree-Law No. 34 of 2021 on Combatting Rumours and Cybercrimes. *SOURCE TO BE VERIFIED*
- [ ] ★ Electronic transactions: Federal Decree-Law No. 46 of 2021 on Electronic Transactions and Trust Services. *SOURCE TO BE VERIFIED*
- [ ] ★ Disability / people of determination: Federal Law No. 29 of 2006 (as amended) on the rights of persons with disabilities. Relevant to the inclusion and "inferred disability" questions. *SOURCE TO BE VERIFIED*
- [ ] ★ Education: federal law(s) on private education, plus Ministry of Education policies on inclusive education and student data / school counselling. *SOURCE TO BE VERIFIED*
- [ ] ★ AI strategy and ethics: UAE National Strategy for Artificial Intelligence 2031, plus any federal AI ethics principles / AI charter published by the AI Office. *SOURCE TO BE VERIFIED*
- [ ] TDRA: regulations or policies on cloud services, ICT data, and IoT (the smart pen is an IoT device). *SOURCE TO BE VERIFIED*
- [ ] Federal advertising / media regulation (advertising to children). *SOURCE TO BE VERIFIED*

## Layer `emirate` (supplementary)
- [ ] ★ Dubai: KHDA inclusive-education policy framework for private schools. *SOURCE TO BE VERIFIED*
- [ ] Dubai: Digital Dubai AI ethics principles and guidelines. *SOURCE TO BE VERIFIED*
- [ ] Abu Dhabi: ADEK policies on inclusion and student data. *SOURCE TO BE VERIFIED*
- [ ] Free zones (note: separate data regimes; tag `emirate` with a `free_zone` domain note): DIFC Data Protection Law; ADGM Data Protection Regulations. *SOURCE TO BE VERIFIED*

## Layer `global_example` (gap analysis only)
- [ ] ★ EU GDPR (Regulation (EU) 2016/679): children's consent (Art. 8), purpose limitation (Art. 5), special categories (Art. 9), automated decision-making (Art. 22), and recitals on children. *SOURCE TO BE VERIFIED*
- [ ] ★ EU AI Act (Regulation (EU) 2024/1689): prohibited practices exploiting vulnerabilities due to age or disability (Art. 5), high-risk education systems (Annex III). *SOURCE TO BE VERIFIED*
- [ ] ★ EU Digital Services Act (Regulation (EU) 2022/2065): ban on profiling-based ads to minors on online platforms (Art. 28). Directly relevant to the judges' escalation step. *SOURCE TO BE VERIFIED*
- [ ] ★ US COPPA (statute + FTC rule, including the most recent amendments). *SOURCE TO BE VERIFIED*
- [ ] ★ UK ICO Age Appropriate Design Code. *SOURCE TO BE VERIFIED*
- [ ] UN CRC General Comment No. 25 (2021) on children's rights in the digital environment. *SOURCE TO BE VERIFIED*
- [ ] UNICEF Policy Guidance on AI for Children. *SOURCE TO BE VERIFIED*
- [ ] UNESCO Recommendation on the Ethics of AI (2021); UNESCO guidance on generative AI in education. *SOURCE TO BE VERIFIED*
- [ ] OECD AI Principles (latest revision). *SOURCE TO BE VERIFIED*

## Standards (tag `global_example`, status `not_legislation`)
- [ ] ★ ITU-T Y.3172 (the PDF is already in the reference repo; still confirm the version). *SOURCE TO BE VERIFIED*
- [ ] ITU AI Readiness framework report (latest). *SOURCE TO BE VERIFIED*

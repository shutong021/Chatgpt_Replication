/*The data used in our analyses are collected from several sources. The conference calls are
obtained from StreetEvents, the product-similarity measure is obtained from the Hoberg
Phillips data library, various financial data come from Compustat and CRSP, CEO com
pensation and ownership data are from Equilar, and Chinese import data are from the UN
Comtrade database. Data availability from the intersection of these sources restricts our
sample to 14 years from 2003 to 2016. We retain firms incorporated in the US and listed
on the NYSE, Amex, or NASDAQ. We further exclude firms in the financial and utilities
sectors, which we define as the Global Industry Classification Standard (GICS) by MSCI
sectors 40 and 55.18 For firms included in the sample, we require all variables used in the
estimation to be non-missing and to have at least five responses in the Q&A portion*/



cd"D:\2025_26 Spring\Replication\Data\Data clean"
*have 318015 uqiue transcript id
use "TranscriptDetails.dta" ,clear
duplicates drop cik,force

*12614 firms (cik id)
keep if cik != ""

*Excluding companies without industry information, as well as financial and public utility companies, there are 5,626 companies.
merge m:1 cik using "corporate information.dta"
keep if _merge == 3
drop _merge
keep if gind != ""
drop if substr(gind,1,2) == "40"
drop if substr(gind,1,2) == "55"
keep transcriptid cik companyid
duplicates drop cik,force
save "Clean_1.dta",replace

*Meetings without QA documentation or with fewer than 5 QA responses were removed; 5547 companies, 172633 meetings.
use "a7fmiti4khrtfmi3.dta",clear
merge m:1 cik using "Clean_1.dta"
keep if _merge == 3
gen count = 1
egen sum = sum(count),by( cik mostimportantdateutc)
drop if sum<5
sort transcriptid componentorder
save "Clean_Q&A.dta",replace



* only remain Q and A
use "Clean_Q&A.dta",clear
keep if inlist(transcriptcomponenttypename, "Question", "Answer")

* keep orignal sequence
gen long __seq = _n

* sort by firm+call，keep internal call sequence
sort cik transcriptid __seq

* For each Question that appears,，let qid +1；backword Answer inherit this qid
by cik transcriptid: gen long qid = sum(transcriptcomponenttypename=="Question")

* If there's an "Answer" at the beginning but no "Question" (or "Abnormality") before it, discard it.
drop if qid==0

*  by cik transcriptid qid (__seq)
sort cik transcriptid qid __seq

* Extract the question text (only values ​​exist in the Question line) and populate it within the question block.
by cik transcriptid qid (__seq): gen strL question = componenttextpreview if transcriptcomponenttypename=="Question"
by cik transcriptid qid: replace question = question[1]

* Concatenate all Answers within the same question block in order.
gen strL answer = ""
by cik transcriptid qid (__seq): replace answer = ///
    trim(cond(_n==1, "", answer[_n-1]) + " " + componenttextpreview) ///
    if transcriptcomponenttypename=="Answer"

* Copy the "finally pieced-together answer" (the last line in the block) to all lines in the block (especially the Question line).
by cik transcriptid qid: replace answer = answer[_N]

* only save Question  => 1 q 1 row with merging answer
keep if transcriptcomponenttypename=="Question"
keep cik transcriptid qid question answer
order cik transcriptid qid question answer

* Treat missing characters as empty strings
replace question = "" if missing(question)
replace answer   = "" if missing(answer)

* Calculate length
gen q_len  = ustrlen(question)
gen a_len  = ustrlen(answer)
gen qa_len = ustrlen(question + answer)

* 166848 pairs,5471 firms
keep if q_len >= 30 & a_len >= 10 & qa_len >= 75

* To randomly sort the data and select the first 1000 as the final data, you need to download the rsort package.
rsort
save "Final.dta", replace
 
/*
duplicates drop cik mostimportantdateutc,force
duplicates drop cik,force
*/


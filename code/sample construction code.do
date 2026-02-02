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
*有318015个uqiue transcript id
use "TranscriptDetails.dta" ,clear
duplicates drop cik,force

*12614个公司(cik id)
keep if cik != ""

*去除无行业信息的公司以及金融业与公共事业公司有5626个公司
merge m:1 cik using "corporate information.dta"
keep if _merge == 3
drop _merge
keep if gind != ""
drop if substr(gind,1,2) == "40"
drop if substr(gind,1,2) == "55"
keep transcriptid cik companyid
duplicates drop cik,force
save "Clean_1.dta",replace

*去除了没有QA文件或QA responses少于5的会议，5547个公司，172633个会议。
use "a7fmiti4khrtfmi3.dta",clear
merge m:1 cik using "Clean_1.dta"
keep if _merge == 3
gen count = 1
egen sum = sum(count),by( cik mostimportantdateutc)
drop if sum<5
sort transcriptid componentorder
save "Clean_Q&A.dta",replace



* 只保留问答（如果数据里还有其他类型，这句很有用）
use "Clean_Q&A.dta",clear
keep if inlist(transcriptcomponenttypename, "Question", "Answer")

* 保留原始行顺序（非常关键）
gen long __seq = _n

* 先按公司+call分组，并保持call内部原始顺序
sort cik transcriptid __seq

* 每出现一个 Question，就让 qid +1；后面的 Answer 继承该 qid
by cik transcriptid: gen long qid = sum(transcriptcomponenttypename=="Question")

* 如果开头有 Answer 但前面没 Question（异常），丢掉
drop if qid==0

* 关键：后面要用 by cik transcriptid qid (__seq)，所以必须按这个顺序排一次
sort cik transcriptid qid __seq

* 提取问题文本（只在 Question 行有值），并在该问题块内填充
by cik transcriptid qid (__seq): gen strL question = componenttextpreview if transcriptcomponenttypename=="Question"
by cik transcriptid qid: replace question = question[1]

* 将同一个问题块内的所有 Answer 按顺序拼接
gen strL answer = ""
by cik transcriptid qid (__seq): replace answer = ///
    trim(cond(_n==1, "", answer[_n-1]) + " " + componenttextpreview) ///
    if transcriptcomponenttypename=="Answer"

* 把"最终拼好的答案"（块内最后一行）复制给该块所有行（尤其是 Question 行）
by cik transcriptid qid: replace answer = answer[_N]

* 只保留 Question 行 => 一问一行（带合并后的答案）
keep if transcriptcomponenttypename=="Question"
keep cik transcriptid qid question answer
order cik transcriptid qid question answer

* 统一把缺失当作空字符串（避免 length(.) 出问题）
replace question = "" if missing(question)
replace answer   = "" if missing(answer)

* 计算长度（Unicode 更稳：ustrlen；如果你确定全是英文也可用 strlen）
gen q_len  = ustrlen(question)
gen a_len  = ustrlen(answer)
gen qa_len = ustrlen(question + answer)

* 按你的三条规则筛选,最终是166848个pairs,5471家公司
keep if q_len >= 30 & a_len >= 10 & qa_len >= 75

* 随机排序，取前一千个作为最终数据，需要下载rsort包
rsort
save "Final.dta", replace
 
/*
duplicates drop cik mostimportantdateutc,force
duplicates drop cik,force
*/

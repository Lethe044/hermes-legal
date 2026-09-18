"""
Contract generator - drafts a new contract from a template, entirely
offline and free. This is the natural complement to the analyzer: instead
of only reviewing a contract someone else sent you, you can produce a
reasonable first draft of your own to send out.

Templates use simple {field} placeholders. Any field the user doesn't
supply is left as a clearly marked placeholder so nothing is silently
wrong - the generated contract always makes clear what still needs to be
filled in before it's used.
"""

from __future__ import annotations

from typing import Dict

CONTRACT_TEMPLATES: Dict[str, Dict] = {
    "nda": {
        "name": "Mutual Non-Disclosure Agreement",
        "fields": ["party_a", "party_b", "effective_date", "term_years", "governing_law"],
        "body": """\
MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement ("Agreement") is entered into as of
{effective_date} ("Effective Date") between {party_a} ("Party A") and
{party_b} ("Party B"), each a "Party" and together the "Parties".

1. Purpose. The Parties wish to explore a potential business relationship
and, in connection with that opportunity, may disclose to each other
certain confidential technical and business information which the
disclosing party desires to protect.

2. Definition of Confidential Information. "Confidential Information"
means any information disclosed by either Party to the other, either
directly or indirectly, in writing, orally, or by inspection of tangible
objects, which is designated as "Confidential" or which reasonably should
be understood to be confidential given the nature of the information and
the circumstances of disclosure.

3. Obligations. Each Party agrees to: (a) hold the other Party's
Confidential Information in strict confidence; (b) not disclose such
Confidential Information to any third party without prior written consent;
and (c) use the Confidential Information only for the purpose of
evaluating the potential business relationship.

4. Exclusions. Confidential Information does not include information that:
(a) is or becomes publicly available through no fault of the receiving
Party; (b) was rightfully known to the receiving Party before disclosure;
(c) is rightfully received from a third party without duty of
confidentiality; or (d) is independently developed without use of the
disclosing Party's Confidential Information.

5. Term. This Agreement and the confidentiality obligations herein shall
remain in effect for {term_years} year(s) from the Effective Date, except
that obligations with respect to trade secrets shall survive for as long
as such information remains a trade secret under applicable law.

6. No License. Nothing in this Agreement grants either Party any rights
to the other Party's Confidential Information beyond the limited right to
use it for the stated purpose.

7. Remedies. Each Party acknowledges that unauthorized disclosure could
cause irreparable harm for which monetary damages would be inadequate,
and that the non-breaching Party is entitled to seek injunctive relief in
addition to any other available remedies.

8. Governing Law. This Agreement shall be governed by and construed in
accordance with the laws of {governing_law}, without regard to its
conflict of laws principles.

9. Entire Agreement. This Agreement constitutes the entire agreement
between the Parties concerning the subject matter herein and supersedes
all prior discussions and agreements, whether written or oral.

IN WITNESS WHEREOF, the Parties have executed this Agreement as of the
Effective Date.

{party_a}                              {party_b}
By: _______________________            By: _______________________
Name:                                   Name:
Title:                                  Title:
""",
    },
    "freelance": {
        "name": "Freelance Service Agreement",
        "fields": ["client_name", "contractor_name", "effective_date", "scope_of_work",
                   "fee_amount", "payment_terms", "term_length", "governing_law"],
        "body": """\
FREELANCE SERVICE AGREEMENT

This Freelance Service Agreement ("Agreement") is entered into as of
{effective_date} between {client_name} ("Client") and {contractor_name}
("Contractor").

1. Scope of Work. Contractor shall provide the following services to
Client: {scope_of_work}. Any changes to the scope must be agreed in
writing by both Parties before additional work begins.

2. Compensation. Client shall pay Contractor {fee_amount} for the services
described above. Payment terms: {payment_terms}. Late payments not
disputed in good faith shall accrue interest at 1.5% per month.

3. Independent Contractor Status. Contractor is an independent contractor,
not an employee of Client. Contractor is responsible for its own taxes,
insurance, and benefits.

4. Intellectual Property. Upon full payment, Contractor assigns to Client
all right, title, and interest in the deliverables created specifically
under the scope of this Agreement. Pre-existing tools, libraries, and
general know-how of Contractor remain Contractor's property and are
licensed to Client for use with the deliverables.

5. Confidentiality. Each Party agrees to keep confidential any proprietary
information disclosed by the other Party during the engagement, for a
period of 3 years following termination of this Agreement.

6. Term and Termination. This Agreement shall remain in effect for
{term_length}, unless terminated earlier by either Party with 30 days'
written notice. Client shall pay for all work satisfactorily completed up
to the effective date of termination.

7. Liability. Neither Party's total liability under this Agreement shall
exceed the total fees paid or payable under this Agreement, except in
cases of gross negligence, willful misconduct, or breach of
confidentiality.

8. Dispute Resolution. Any dispute arising from this Agreement shall first
be addressed through good-faith negotiation, and if unresolved, through
mediation before either Party pursues other remedies. Costs of mediation
shall be shared equally.

9. Governing Law. This Agreement shall be governed by the laws of
{governing_law}.

10. Entire Agreement. This Agreement constitutes the entire understanding
between the Parties and supersedes all prior agreements relating to its
subject matter.

{client_name}                          {contractor_name}
By: _______________________            By: _______________________
Date:                                   Date:
""",
    },
    "employment": {
        "name": "Employment Agreement",
        "fields": ["employer_name", "employee_name", "job_title", "start_date",
                   "salary", "employment_type", "notice_period_days", "governing_law"],
        "body": """\
EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is entered into as of {start_date}
between {employer_name} ("Employer") and {employee_name} ("Employee").

1. Position. Employee is hired for the position of {job_title}, reporting
to Employer's designated manager, on a {employment_type} basis.

2. Compensation. Employer shall pay Employee a salary of {salary}, payable
in accordance with Employer's standard payroll schedule, subject to
applicable withholdings.

3. Duties. Employee shall perform the duties customarily associated with
the position of {job_title} and such other duties as reasonably assigned
by Employer.

4. Confidentiality. Employee agrees to maintain the confidentiality of
Employer's proprietary and business information both during and after
employment, for a period of 3 years following termination.

5. Intellectual Property. Any work product created by Employee within the
scope of employment and using Employer's resources belongs to Employer.
This does not extend to work created entirely on Employee's own time,
using Employee's own resources, and unrelated to Employer's business.

6. Termination. Either Party may terminate this Agreement by providing at
least {notice_period_days} days' written notice, except in cases of
termination for cause, which may be immediate.

7. Non-Compete. For a period of 12 months following termination, Employee
shall not work for a direct competitor of Employer within the same
regional market, to the extent enforceable under applicable law.

8. Governing Law. This Agreement is governed by the laws of
{governing_law}.

9. Entire Agreement. This Agreement constitutes the entire agreement
between the Parties regarding the subject matter herein.

{employer_name}                        {employee_name}
By: _______________________            Signature: _______________________
Date:                                   Date:
""",
    },
    "service": {
        "name": "General Service Agreement",
        "fields": ["provider_name", "customer_name", "effective_date", "services_description",
                   "fees", "payment_schedule", "term_length", "governing_law"],
        "body": """\
SERVICE AGREEMENT

This Service Agreement ("Agreement") is entered into as of
{effective_date} between {provider_name} ("Provider") and {customer_name}
("Customer").

1. Services. Provider shall provide the following services to Customer:
{services_description}.

2. Fees and Payment. Customer shall pay Provider {fees}. Payment schedule:
{payment_schedule}.

3. Term. This Agreement shall remain in effect for {term_length}, and may
be renewed by written agreement of both Parties. Either Party may
terminate this Agreement with 30 days' written notice.

4. Warranties. Provider warrants that services will be performed in a
professional and workmanlike manner consistent with industry standards.

5. Limitation of Liability. Provider's total liability under this
Agreement shall not exceed the total fees paid by Customer in the 12
months preceding the claim, except for liability arising from gross
negligence or willful misconduct.

6. Confidentiality. Each Party shall keep confidential any proprietary
information received from the other Party in connection with this
Agreement.

7. Governing Law. This Agreement is governed by the laws of
{governing_law}.

8. Entire Agreement. This Agreement, together with any exhibits, is the
entire agreement between the Parties regarding its subject matter.

{provider_name}                        {customer_name}
By: _______________________            By: _______________________
Date:                                   Date:
""",
    },
}


def generate_contract(template_key: str, answers: Dict[str, str]) -> str:
    tpl = CONTRACT_TEMPLATES[template_key]
    values = {}
    for field in tpl["fields"]:
        values[field] = answers.get(field) or f"[{field.upper().replace('_', ' ')}]"
    return tpl["body"].format(**values)

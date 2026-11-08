import copy
import json
import unittest
from quality_lab.core import ROOT, load_cases, search, run_agent, score, evaluate, redact
from quality_lab.statistics import compare

class LabTests(unittest.TestCase):
    def setUp(self):
        self.prompts = json.loads((ROOT/'data/prompts.json').read_text())

    def test_tenant_and_principal_authorization(self):
        self.assertEqual(search('acme','member','secret'), [])
        docs = search('acme','admin','secret')
        self.assertTrue(docs)
        self.assertTrue(all(d['tenant']=='acme' for d in docs))
        self.assertEqual(search('acme','outsider','launch'), [])

    def test_invalid_citation_gates_quality(self):
        case = load_cases('dev')[0]
        response = run_agent(case,self.prompts['candidate'])
        response.citations = ['other-launch-0']
        self.assertEqual(score(case,response)['quality'], 0)

    def test_fallback_and_abstention(self):
        case = next(c for c in load_cases('dev') if c['topic']=='secret')
        response = run_agent(case,self.prompts['candidate'],'broken')
        self.assertTrue(response.fallback)
        self.assertEqual(response.provider,'strong')
        self.assertEqual(response.citations,[])
        self.assertNotIn('90000',response.answer)

    def test_labels_do_not_change_agent_response(self):
        case = load_cases('dev')[0]
        changed = dict(case,required=['unrelated'],forbidden=['Friday'],split='holdout')
        a = run_agent(case,self.prompts['baseline'])
        b = run_agent(changed,self.prompts['baseline'])
        self.assertEqual((a.answer,a.provider,a.citations),(b.answer,b.provider,b.citations))

    def test_candidate_repairs_known_failures(self):
        a = evaluate(self.prompts['baseline'])
        b = evaluate(self.prompts['candidate'])
        self.assertGreater(b['mean_quality'],a['mean_quality'])
        self.assertTrue(all(r['scores']['safety']==1 for r in b['rows']))

    def test_paired_comparison_and_mismatch(self):
        a = evaluate(self.prompts['candidate'])
        b = copy.deepcopy(a)
        for r in b['rows']:
            r['scores']['quality']=0
        self.assertEqual(compare(a,b)['status'],'regression')
        self.assertEqual(compare(a,a)['status'],'inconclusive')
        b['dataset_sha256']='changed'
        with self.assertRaises(ValueError):
            compare(a,b)
        b = copy.deepcopy(a)
        b['rows'].pop()
        with self.assertRaises(ValueError):
            compare(a,b)

    def test_redaction(self):
        self.assertEqual(redact('Contact ada@example.test now'),'Contact [EMAIL] now')

if __name__ == '__main__':
    unittest.main()

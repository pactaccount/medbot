"""Promote explicitly approved human corrections and compare versioned runs."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import run as evaluator


def promote(report_path, dataset_path, output):
    report=json.loads(report_path.read_text())
    if evaluator.digest(dataset_path)!=report['dataset_sha256']:
        raise ValueError('Dataset differs from the reviewed run')
    cases={r['id']:r for r in json.loads(dataset_path.read_text())}
    promoted=[]
    for row in report['cases']:
        review=row.get('human_review',{})
        if review.get('approved_for_regression') is not True:
            continue
        if not isinstance(review.get('correction'),str) or not review['correction'].strip():
            raise ValueError('An approved regression needs a written correction: '+row['id'])
        evaluator.validate_review(review)
        case=deepcopy(cases[row['id']])
        case['reference']=review['correction']
        case['feedback_provenance']={'reviewed_report_sha256':evaluator.digest(report_path),
                                     'original_reference':cases[row['id']]['reference'],
                                     'review':review}
        promoted.append(case)
    if not promoted:
        raise ValueError('No explicitly approved corrections; no dataset was written')
    if output.exists():
        raise ValueError('Choose a new regression filename; prior versions are immutable')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(promoted,indent=2)+'\n')
    return len(promoted)


def compare(before_path, after_path):
    before=json.loads(before_path.read_text()); after=json.loads(after_path.read_text())
    if before['dataset_sha256']!=after['dataset_sha256']:
        raise ValueError('Compare versions on the same dataset, not different questions')
    if before['policy_sha256']!=after['policy_sha256']:
        raise ValueError('Reference policy changed; do not attribute the difference solely to agent changes')
    old={r['id']:r for r in before['cases']}; new={r['id']:r for r in after['cases']}
    paired=[]
    for key in sorted(old.keys() & new.keys()):
        a,b=old[key],new[key]
        if a['status']!='completed' or b['status']!='completed':
            continue
        paired.append({'id':key,'before':all(a['checks'].values()),'after':all(b['checks'].values())})
    return {'before':evaluator.aggregate(before),'after':evaluator.aggregate(after),
            'same_configured_model':before['model']==after['model'],
            'paired_completed_cases':len(paired),
            'improved':[r['id'] for r in paired if not r['before'] and r['after']],
            'regressed':[r['id'] for r in paired if r['before'] and not r['after']],
            'note':'Deterministic checks do not establish semantic accuracy or absence of hallucinations.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    promote_parser=commands.add_parser('promote')
    promote_parser.add_argument('report',type=Path)
    promote_parser.add_argument('--dataset',type=Path,default=Path(__file__).with_name('development.json'))
    promote_parser.add_argument('--output',type=Path,required=True)
    comparison=commands.add_parser('compare')
    comparison.add_argument('before',type=Path); comparison.add_argument('after',type=Path)
    args=parser.parse_args()
    if args.command=='promote':
        print('Approved regression cases:',promote(args.report,args.dataset,args.output))
    else:
        print(json.dumps(compare(args.before,args.after),indent=2))

if __name__=='__main__': main()

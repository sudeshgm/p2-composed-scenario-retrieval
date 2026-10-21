"""Plain everyday-English wording for programs and modification texts (user feedback: m was hard to read)."""
NOUN={'VEHICLE':'vehicle','CAR':'car','TRUCK':'truck','BUS':'bus','PEDESTRIAN':'pedestrian','BICYCLIST':'cyclist','EGO':'our own car'}
def is_ped(g): return g in ('PEDESTRIAN','BICYCLIST')
def st(s,g):
    if s=='moving': return 'walking' if g=='PEDESTRIAN' else ('riding along' if g=='BICYCLIST' else 'driving along')
    if s=='stationary': return 'standing still' if is_ped(g) else 'parked'
    return {'accelerating':'speeding up','braking':'slowing down','turning_left':'turning left','turning_right':'turning right',
            'changing_lanes':'changing lanes','at_ped_crossing':'on a crosswalk','on_road':'on the road','near_intersection':'near a junction'}[s]
# relation phrased as "<a> ... the <b>"
REL={'in_same_lane':'is driving in the same lane as the {b}','heading_toward':'is moving toward the {b}',
     'following':'is driving right behind the {b}, following it','near':'is close to the {b}',
     'facing_toward':'is pointed at the {b}','dir_forward':'has the {b} in front of it','dir_backward':'has the {b} behind it',
     'dir_left':'has the {b} on its left','dir_right':'has the {b} on its right'}
SIDE={'dir_forward':'in front of','dir_backward':'behind','dir_left':'on the left of','dir_right':'on the right of'}
def the(g): return 'our own car' if g=='EGO' else 'the '+NOUN[g]
def noun_b(p,role='b'):
    g=p[role]['cat']; n=NOUN[g]
    if p.get('a') and p['b'] and role=='b' and p['a']['cat']==g: n='other '+n
    return n
def desc(p):
    g=p['a']['cat']; s=[st(x,g) for x in p['a']['states']]
    head=('Our own car' if g=='EGO' else 'A '+NOUN[g])+(' that is '+' and '.join(s) if s else '')
    if not p.get('rel'): return head
    ADJ={'moving':'moving','stationary':'standing' if is_ped(p['b']['cat']) else 'parked'}
    bs=[ADJ.get(x,st(x,p['b']['cat'])) for x in p['b']['states']]
    n=noun_b(p); b=(n.replace('other ','other '+' '.join(bs)+' ') if n.startswith('other ') else ' '.join(bs)+' '+n) if bs else n
    r=REL[p['rel']].format(b=b)
    return head+(' and ' if s else ' that ')+r
def m_text(fam,P,Pp):
    A=the(P['a']['cat'])
    if fam=='relational':
        b=noun_b(P); new=REL[Pp['rel']].format(b=b); old=REL[P['rel']].replace('is ','',1).format(b=b)
        old=old.replace('the '+b,'it') if P['rel']!='near' else 'just close to it'
        if P['rel']=='near': return f"The same, but {A} {new}, not just close to it."
        return f"The same, but {A} {new} - not {old}."
    if fam=='directional':
        b=noun_b(P); return f"The same, but the {b} is {SIDE[Pp['rel']]} {A} now, not {SIDE[P['rel']]} it."
    if fam=='agent_class':
        if P['a']['cat']!=Pp['a']['cat']:
            return f"The same situation, but with a {NOUN[Pp['a']['cat']]} doing it instead of a {NOUN[P['a']['cat']]}."
        return f"The same, but the other road user is a {NOUN[Pp['b']['cat']]}, not a {NOUN[P['b']['cat']]}."
    if fam=='state':
        g=P['a']['cat']; old=[x for x in P['a']['states'] if x not in Pp['a']['states']][0]; new=[x for x in Pp['a']['states'] if x not in P['a']['states']][0]
        o=st(old,g)
        if old=='moving' and new in ('accelerating','braking'): o='driving at a steady speed' if not is_ped(g) else 'moving at a steady pace'
        return f"The same, but {A} is {st(new,g)} rather than {o}."
    if fam=='compositional':
        new=[x for x in Pp['a']['states'] if x not in P['a']['states']][0]
        return f"The same, but {A} is also {st(new,P['a']['cat'])}."
    raise ValueError(fam)
def why_not(t):
    f,P,Q=t['family'],t['P'],t['Pp']; g=P['a']['cat']; A=the(g)
    new=lambda a,b:[x for x in b if x not in a]
    if f=='state':
        o=new(Q['a']['states'],P['a']['states'])[0]; n=new(P['a']['states'],Q['a']['states'])[0]
        return f"It fits the old search, but it is {st(o,g)}, not {st(n,g)}."
    if f=='compositional':
        return f"It fits the old search, but it is not {st(new(P['a']['states'],Q['a']['states'])[0],g)}."
    if f=='relational':
        return f"It fits the old search, but it {REL[Q['rel']].format(b=noun_b(P)).replace('is ','is not ',1).replace('has ','does not have ',1)}."
    if f=='directional':
        return f"It fits the old search, but the {noun_b(P)} is {SIDE[P['rel']]} it, not {SIDE[Q['rel']]} it."
    # agent_class: negative is of the NEW class but misses one other part of the new search
    nc=NOUN[Q['a']['cat']] if P['a']['cat']!=Q['a']['cat'] else NOUN[Q['b']['cat']]
    if Q['a']['states']: miss=f"{the(Q['a']['cat'])} is not {st(Q['a']['states'][-1],Q['a']['cat'])}"
    elif Q.get('rel') and P['a']['cat']!=Q['a']['cat']: miss="it does not "+REL[Q['rel']].format(b=noun_b(Q)).replace('is ','be ',1).replace('has ','have ',1)
    elif Q.get('rel'): miss="the scene does not match the rest of the new search ("+desc(Q).lower()+")"
    else: miss='it misses another part of the new search'
    who='It is a '+nc if P['a']['cat']!=Q['a']['cat'] else 'The other road user is a '+nc
    return f"{who}, as the new search asks, but {miss}."
JARGON=['heading toward','facing toward','instead of being','P\'','conjunct']

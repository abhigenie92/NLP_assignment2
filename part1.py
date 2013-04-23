import json
import string
import time
from collections import defaultdict

nonterminal_counts = defaultdict(float)   #counts of S,NP,etc
unary_rule_counts = defaultdict(float)   #counts of X -> word
binary_rule_counts = defaultdict(float)  #counts of X -> Y Z
word_counts = defaultdict(float)         #counts of words
counts_loaded = False


def load_counts(countsfile):
    global nonterminal_counts
    global unary_rule_counts
    global binary_rule_counts
    global counts_loaded
    
    with open(countsfile,"r") as f:
        for line in f:
            items = line.replace('\n','').split(' ')
            if items[1] == 'BINARYRULE':
                binary_rule_counts[(items[2],items[3],items[4])] = float(items[0])
            elif items[1] == 'NONTERMINAL':
                nonterminal_counts[items[2]] = float(items[0])
            else:
                unary_rule_counts[(items[2],items[3])] = float(items[0])
                word_counts[items[3]] += float(items[0])
    counts_loaded = True

def is_rare(candidate_word):
    #print 'rare test for:',candidate_word,'count:',word_counts[candidate_word]
    return (word_counts[candidate_word] < 5)

def modify_train_file(path):
    assert counts_loaded
    i = 1
    with open(path,"r") as f:
        with open(path + '.modified', 'w') as fout:
            for line in f:
                #print 'line',i,'processed'
                i += 1
                tree = json.loads(line)
                tree = modify_tree(tree)
                fout.write(json.dumps(tree) + '\n')


def modify_tree(tree):
    #if this is a leaf, change the word to _RARE_ if its rare
    #else, modify all (max two) leaves
    if isinstance(tree[1],unicode):
        if is_rare(tree[1]):
            tree[1] = u"_RARE_"
        return tree
    else:
        if len(tree) < 2:
            print tree
        i = 1
        while (len(tree) > i):
            modify_tree(tree[i])
            i += 1
        return tree


def rule_prob(root, left, right):
    #assert counts_loaded
    return (float(binary_rule_counts[(root,left,right)])
                 / float(nonterminal_counts[root]))

def emission_prob(root,terminal):
    #assert counts_loaded
    if is_rare(candidate_word=terminal):
        #print terminal,'is rare.'
        return (float(unary_rule_counts[(root,u"_RARE_")])
                / float(nonterminal_counts[root]))
    return (float(unary_rule_counts[(root,terminal)])
            / float(nonterminal_counts[root]))

def parse_tree_from_words(words,N,R,rules_lookup):
    start_time = time.time()
    #cky logic here.
    pi = {} #dynamic lookup table
    bp = {} #backpointer lookup table
    n = len(words)
    for i, word in enumerate(words):
        rare = is_rare(word)
        tmpword = word
        if rare:
            tmpword = '_RARE_'
        for x in N:
            if unary_rule_counts[(x,tmpword)] == 0:
                pi[(i,i,x)] = 0.0
            else:
                pi[(i,i,x)] = emission_prob(root=x,terminal=tmpword)
                bp[(i,i,x)] = [(x,word),i]

    # ---------End Initialization, Begin Algorithm----------------

    for curlen in xrange(0,n-1):
        for i in xrange(0,n-curlen-1):
            j = i + curlen + 1
            for x in N:
                best_rule = ('','','')
                best_split = 1.0
                current_best_prob = 0.0
                for s in xrange(i,j):
                    for (X,Y,Z) in rules_lookup[x]:
                        #if X != x: break
                        
                        test_prob = (
                                    ((binary_rule_counts[(X,Y,Z)])
                                     / (nonterminal_counts[X]))
                                     * (pi[(i,s,Y)])
                                     * (pi[(s+1,j,Z)])
                                    )
                        
   
                        if test_prob > current_best_prob:
                            
                            best_rule = (X,Y,Z)
                            best_split = s
                            current_best_prob = test_prob
                
                pi[(i,j,x)] = current_best_prob
                bp[(i,j,x)] = [best_rule,best_split]

    # ----------- End Algorithm, Begin tree reconstruction. ---------------
    
    tree = construct_tree(bp=bp,i=0,j=n-1,root='SBARQ')
    end_time = time.time()
    print end_time-start_time
    return tree

def construct_tree(bp,i,j,root):    
    rule, split = bp[(i,j,root)][0], bp[(i,j,root)][1]
    if len(rule) == 2:
        #base case. 
        return [root, rule[1]]
    else:
        #recursive step
        return [root,
                construct_tree(bp,i,split,rule[1]),
                construct_tree(bp,split+1,j,rule[2])]

def read_and_parse(tree_file,out_file):
    assert counts_loaded
    N = set(nonterminal_counts.keys())
    R = set(binary_rule_counts.keys())
    rules_lookup = defaultdict(set)

    for (x,y,z) in R:
        rules_lookup[x].add((x,y,z))
        
    #print 'n:',len(N),'r:',len(R)
    with open(tree_file, 'r') as fin:
        with open(out_file, 'w') as fout:
            i = 1
            for line in fin:
                words = line.replace('\n','').split(' ')
                tree = parse_tree_from_words(words=words,N=N,R=R, rules_lookup = rules_lookup)
                fout.write(json.dumps(tree) + '\n')
                #print 'finished:',i
                i += 1
                #raw_input("press ENTER to continue.")

                
load_counts('counts_vert_modified.dat')
#modify_train_file("parse_train_vert.dat")
#parse_tree_from_words(['What','are','geckos','?'], set(nonterminal_counts.keys()),
#                      set(binary_rule_counts.keys()))

read_and_parse('parse_test.dat','parse_test.p3.out')

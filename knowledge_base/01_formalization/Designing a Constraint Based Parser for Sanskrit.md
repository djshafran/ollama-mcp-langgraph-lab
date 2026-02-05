

Source: [Designing a Constraint Based Parser for Sanskrit](https://sanskrit.uohyd.ac.in/faculty/amba/PUBLICATIONS/papers/constraint_parser_revised.pdf)

Amba Kulkarni, Sheetal Pokar, and Devanand Shukl

Department of Sanskrit Studies,

University of Hyderabad,

Hyderabad

apksh@uohyd.ernet.in,{sjpokar,dev.shukl}@gmail.com

**Abstract.** Verbal understanding (´sa¯bdabodha) of any utterance requires the knowledge of how words in that utterance are related to each other. Such knowledge is usually available in the form of cognition of grammatical relations. Generative grammars describe how a language codes these relations. Thus the knowledge of what information various grammatical relations convey is available from the generation point of view and not the analysis point of view. In order to develop a parser based on any grammar one should then know precisely the semantic content of the grammatical relations expressed in a language string, the clues for extracting these relations and finally whether these relations are expressed explicitly or implicitly. Based on the design principles that emerge from this knowledge, we model the parser as finding a directed Tree, given a graph with nodes representing the words and edges representing the possible relations between them. Further, we also use the M¯ıma¯m˙ sa¯ constraint of ¯aka¯n˙ks.¯a (expectancy) to rule out non-solutions and sannidhi (proximity) to prioritize the solutions. We have implemented a parser based on these principles and its performance was found to be satisfactory giving us a confidence to extend its functionality to handle the complex sentences.[[1]](#_ftn1)

**Key Words:** Sanskrit, Constraint Based Parser, Information coding,

_¯ak¯an˙ks.¯a_, _sannidhi_.

# 1         Introduction

_S¯abdabodha__´_ is the understanding that arises from a linguistic utterance. The three schools of S¯abdabodha viz.´ _Vya¯karan. a_, _Nya¯ya_ and _M¯ım¯ams¯a_ mainly differ in the chief qualificand of the S¯abdabodha. Nevertheless to begin with,´ all these three schools need an analysis of an utterance. This analysis expresses the relations between different meaningful units involved in an utterance. The utterance may be as small as a single word or as big as a complete novel. In what follows, however, we take a sentence[[2]](#_ftn2) as a unit, and as such we discuss only the relations of words within a sentence and do not deal with the discourse analysis.

A generative grammar of any language provides rules for generation. For analysis, we require a mechanism by which we can use these rules in a reverse way. The reversal in some cases is easy and also deterministic. For example, subtraction is an inverse operation of addition and is deterministic. The reversal may not always be deterministic. Let us see a simple example of non-deterministic reversal with which all of us are familiar. The multiplication tables or simple method of repetitive addition provides a mechanical way for multiplication. Given a product, to find its factors is a reverse process. Multiplication of two numbers, say, 4 and 3 produces a unique number 12. But its decomposition into two factors is not unique. 12 may be decomposed into two factors as either {6,2} or {4,3} in addition to a trivial decomposition {12,1}. Thus the inverse process may at times involve non-determinism. Depending upon the context, if one factor is known, the other factor gets fixed. For example, if you are interested in distributing 12 apples among 2 children, then one of the factors being 2, the other factor, viz. 6, is determined uniquely.

This is true of a generative grammar as well. To give an example, look at the following two su¯tras of Pa¯n.ini.

–    anabhihite (2.3.1)

–    kartr.karan.ayos tr.t¯ıy¯a (2.3.18)

These two su¯tras together, in case of a passive voice (karman.i prayogah.), assign third case[[3]](#_ftn3) to both the kart¯a as well as karan.am ka¯raka as in

(1) _r¯amen. a ba¯n. ena va¯lih. hanyate_.

Now, when a hearer (who knows Sanskrit grammar) listens to this utterance, he notices two words ending in the third case suffix and that the construction is in passive voice. But unless he knows that _r¯ama_ is the name of a person and _ba¯n. a_ is used as an instrument, he fails to get the correct reading. In the absence of such an ‘extra-linguistic’ knowledge, there are two possible interpretations viz. either _r¯ama_ is kart¯a and _ba¯n. a_ is karan.am, or _ba¯n. a_ is kart¯a and _r¯ama_ is karan.am leading to a non-determinism.[[4]](#_ftn4)

The process of analysing a sequence of words to determine the underlying grammatical structure with respect to a grammar is parsing. There are two distinct ways of developing a parser for a language. The first method which has gained recent predominance is to use statistical machine learning techniques to learn from a manually annotated corpus. This requires a large human annotated corpus. Second method is to use the grammar rules of generation to ‘guess’ the possible solutions and apply constraints to rule out obvious non-solutions. There have been notable efforts in developing parsers by both the statistical methods as well as grammar based methods for various languages (Lin,1998; Marneffe, 2006; Sleator,1993). A parser based on Pa¯n.inian Grammar Formalism for modern Indian languages is described in Bharati, et. al. (1995; 85-100). This parser is modeled as a bipartite graph matching problem. A statistical parser for analysing Sanskrit is described in Hellwig (2008). The shallow parser of Huet (2006, 2009) uses bare minimum information of transitivity of a verb as a sub-categorisation frame and models it as a graph-matching algorithm. The main purpose of this shallow parser is to filter out non-sensical interpretations. It is therefore natural for Huet to develop small tools such as ‘ca’ handler with more priority to rule out non-grammatical solutions (rather than to develop a full-fledged parser)

While designing a grammar based parser, two major design issues[[5]](#_ftn5) one has to address are: a) what should be the level of semantic analysis, and b) which relations to represent in the parsed output. In order to decide on these issues, in what follows, we first look at the Sanskrit grammar to see what kind of semantic relations can be extracted from a language string, precisely where is the information about these relations coded, and whether the extracted relations are from primary sources or secondary. Later we discuss the issues the mechanical processing throws up, and the possible ways to handle them. Based on these observations, we decide various design parameters. The next section discusses mathematical formulation of the problem, its implementation and finally its performance analysis.

# 2         Encoding of grammatical relations in Sanskrit

Parsing unfolds a linear string of words into a structure which shows explicitly the relations between words. For example, the parse of

(2)  _r¯aja¯ vipra¯ya ga¯m˙ dad¯ati._

may be described as in Figure 1.

The task of a parser involves identifying various relations between the words. So the parser developer should decide on the nature of relations and the means to identify the relations. Sanskrit has the unique privilege of having an extant grammar in the form of As.t.¯adhya¯y¯ı. It has been demonstrated (Bharati, forthcoming) that Pa¯n.ini had given utmost importance to the information coding and the dynamics of information flow in a language string. In what follows we

![](file:///C:/Users/ivan.MODULEMAX/AppData/Local/Packages/oice_16_974fa576_32c1d314_3514/AC/Temp/msohtmlclip1/01/clip_image002.jpg)

**Fig.1.** semantic relations

look at the information coding in Sanskrit from the point of view of designing a parser.

**2.1          Semantic content of the relations**

Though the correspondence between the semantic relations and the ka¯raka relations is duly stated in the grammar, what is encoded in words is only the ka¯raka relations. There is no one-to-one relation between thematic and ka¯raka relations. One ka¯raka relation may correspond to more than one thematic relation and one thematic relation may be realised by more than one ka¯raka relations (Kiparsky, 2009: 49). What can be extracted from a language string alone without using any extra-linguistic information are the syntactico-semantic relations or the ka¯raka relations and not the pure semantic relations. We give below some examples in our support.

Svatantrah. kart¯a The va¯rttikas under Pa¯n.ini’s su¯tra _ka¯rake_ (1.4.23) go like this6

In the sentence _devadattah. pacati_, the activity of cooking refers to the activity of devadattah. viz. putting a vessel on the stove, pouring water in it, adding rice, supplying the fuel etc. and this activity refers to the activity of the pradha¯na kart¯a. In the sentence _stha¯l¯ı pacati_, the cooking activity refers to holding the rice and water till the rice cooks and this activity is that of a vessel. In the sentence _edha¯h. paks.yanti_, the cooking activity refers to the supply of sufficient heat by a piece of firewood and thus refers to the activity of an instrument.

![](file:///C:/Users/ivan.MODULEMAX/AppData/Local/Packages/oice_16_974fa576_32c1d314_3514/AC/Temp/msohtmlclip1/01/clip_image003.gif)

6 adhi´srayan.odak¯asecanatan.d.ula¯vapanaidho’pakars.an.akriya¯h. pradh¯anasya kartuh. p¯akah. ||(ma. bh¯a. 1.4.23. v¯a 8) || dron.am˙ pacaty¯ad.hakam˙ pacat¯ıti sam˙ bhavanakriya¯ dh¯aran.akriy¯a ca¯dhikaran.asya p¯akah. ||(ma. bh¯a. 1.4.23.v¯a 9 )|| edh¯ah. paks.yanty¯a viklitter jvalis.yant¯ıti jvalanakriya¯ karan.asya p¯akah. ||(ma. bh¯a.

1.4.23.v¯a 10) ||

In real world, _devadattah._, _stha¯l¯ı_ and _edha¯h._ are the agent, locus and the instrument respectively. But what is expressed by these language strings is just the _kartr.tva_ of the pradha¯na kart¯a, adhikaran.am and karan.am respectively and NOT the agent, locus and instrument.

**´ses****.e** Similarly the relation between _vr.ks.a_ and _´sa¯kh¯a_, _pitr._ and _putra_, and _r¯ajan_ and _purus.a_ in the phrases _vr.ks.asya ´sa¯kh¯a_, _pituh. putra.h_ and _r¯ajn˜ah. purus.ah._ is marked by the genitive case suffix, and Pa¯n.ini groups all of them under the su¯tra _´sas..th¯ı ´ses.e_ (2.3.50). Semantically however the first is avayava-avayav¯ı-bha¯va (part-whole-relation), the second one is janya-janaka-bha¯va (parent-child-relation), and the third one is sva-sv¯ami-bha¯va (owner-possession-relation).

adhi´s¯ın˙sth¯as¯am˙ karma **(1.4.46)** In the sentences

(3)  _harih. vaikun..tham adhi´sete._

(4)  _munih. ´sil¯apat..tam adhitis..thati._

(5)  _sa¯dhuh. parvatam adhya¯ste._

_vaikun..tha_, _´sil¯apat..ta_ and _parvata_ are in the second case, and Pa¯n.ini assigns them a karma role. However, semantically, all of them are the loci of the activities of the associated verbs viz. adhi-´s¯ın˙, adhi-sth¯a, and adhi-a¯s. Hence the naiya¯yikas, who want to map the ‘world of words’ to the real world, find it difficult to accept the karmatva of these words and they qualify this karmatva on the second case ending as _¯adh¯arasya anu´sa¯sanika-karmatva_ (Dash, 1991;141). Thus, there is a deviation between the real world and what is expressed through the words.

sahayukte ’apradha¯ne (2.3.19) In the sentence,

(6)  _ma¯tr¯a saha ba¯lakah. ¯agacchati._

the agreement of the verb is with _ba¯lakah._, and not with _ma¯tar¯a_. According to the su¯tra (2.3.19), ‘saha’ is used with the apradha¯na (sub-ordinate) ka¯raka. Thus in this example, _ma¯ta¯_ is sub-ordinate and _ba¯laka_ is the main kart¯a. However, at another level of semantic analysis, the situation is reversed. It is _ma¯ta¯_ who carries the child in her arms and thus _ba¯laka_ is apradha¯na and _ma¯ta¯_ is the pradha¯na ka¯raka. Thus again there is a mismatch between the reality and what sentence actually codes in terms of grammatical relations.

From all the above examples, it is clear that the world of words (´sabda-jagat) is different from the real world. To match the extracted relations with the experience of the real world, extra-linguistic information is needed. Since the extra-linguistic information is not easily accessible, and is open ended, we would extract only syntactico-semantic relations that depend solely upon the linguistic / grammatical information in a sentence.

**2.2             Clues for extracting the relations**

Sanskrit being inflectionally rich, we know that suffixes mark the relation between words. Similarly certain indeclinables mark some grammatical relations. Agreement between the words also indicate certain grammatical relations. We discuss below these cases with examples.

1.    Abhihitatva

The Pa¯n.inian su¯tra ‘anabhihite’ (2.3.1) (if not already expressed) is an important su¯tra that governs the vibhakti assignment to the nominals. The va¯rttika[[6]](#_ftn6) on this su¯tra explains abhihita as the one which is expressed either by tin˙ (a finite verbal suffix), kr.t (a non-finite verbal suffix), taddhita (derivational nominal suffix) or sama¯sa (compound). E.g. in the sentence

(7)  _r¯amah. vanam˙ gacchati._

the verb being in the active voice (kartari prayogah.), the verbal suffix ‘ti’ expresses the kart¯a, while in the following sentence in passive voice (karmani. prayogah.)

(8)  _r¯amen. a vanam˙ gamyate._

the karma is expressed by the verbal suffix. As such, in both cases, the one which is expressed (kart¯a and karma respectively) is in the nominative case and shows number and person agreement with the verb form. Some of the kr.t suffixes also express the ka¯rakas. For example, in

(9)  _dha¯van a´svah.._

the kr.t suffix in ‘dha¯van’ expresses the relation of kart¯a (kartari kr.t (3.4.68)).

2.    Vibhakti

The verbal as well as nominal suffixes in Sanskrit are termed vibhaktis. We have already seen that verbal suffixes (_tin˙_), through abhihitatva, mark the relations between words. Now we consider the nominal suffixes. They fall under two categories.

(a)    vibhakti indicating a ka¯raka relation

This marks a relation between a noun and a verb known as a ka¯raka relation. Sanskrit uses seven case suffixes to mark six ka¯raka relations viz. _karta¯_, _karma_, _karan. a_m, _samprada¯na_m, _apa¯da¯na_m and _adhikaran. a_m. The genitive suffix, in addition to marking a ka¯raka relation[[7]](#_ftn7), is predominantly used to mark the noun-noun relation. There is no one-to-one mapping between the case suffixes and the ka¯raka relations, which makes it difficult to determine the relation on the basis of vibhakti alone.

(b)    upapada vibhakti

In addition to the noun-noun relations expressed by the sixth case, there are certain words, most of them indeclinables called upapadas, which also mark a special kind of noun-noun relation. These indeclinables, mark a relation of a noun with an another noun, and in turn demand a special case suffix for the preceding noun. For example, the upapada ‘saha’ demands a third case suffix for the preceding noun as in

(10) _r¯amen. a saha s¯ıta¯ vanam˙ gacchati._

3.    Indeclinables (avyaya)

The indeclinables mark various kinds of relations such as negation, adverbial(manner adverbs only), co-ordination, etc. Sometimes they also provide information about interrogation, emphasis, etc. We distinguish the upapadas from the avyayas, mainly because, though most of the upapadas are also indeclinables, they demand a special case suffix on the preceding word, whereas it is not so with indeclinables.

For example, the relation of ‘na’ with ‘gacchati’ in the sentence

(11)  _r¯amah. gr.ham˙ na gacchati._

is that of ‘negation(nis.edha)’. Similarly, the relation of ‘mandam’ with ‘calati’ in the sentence

(12)  _r¯amah. mandam˙ calati._

is that of ‘adverbial(kriy¯avi´ses.an.a)’. The relation of ‘eva’ with ‘r¯ama’ in the sentence

(13)  _r¯amah. eva tatra upavis..tati._

is that of ‘emphasis(avadha¯ran.a)’.

4.    Sam¯an¯adhikaran.a

Agreement in gender, number and case suffix marks _sam¯an¯adhikaran. a_ (having the same locus), or the modifier-modified relation between two nouns as in

(14)  _´svetah. a´svah. dha¯vati._

(15)  _a´svah. ´svetah. asti._

In (14) as well as (15), the words _a´svah._ and _´svetah._ have the same gender, number and vibhakti indicating sama¯n¯adhikaran.a. However, there is a slight difference between the information being conveyed. In (15), the word _´svetah._ is a predicative adjective (vidheya vi´ses.an.a), while in (14) it is an attributive adjective.

**2.3           Explicit Versus Implicit relations**

Relations need not always be encoded directly through suffixes or morphemes. Sometimes the information is coded in the ‘Language Convention’. The su¯tra

sama¯nakartr.kayoh. pu¯rvaka¯le (3.4.21)

states that the suffix _ktva¯_ is used to denote the preceding of two actions that share the same kart¯a. Then the question is what relation does _ktva¯_ suffix mark? - the relation of kartr.tva or the relation of pu¯rvaka¯l¯ınatva? or both? Bhartr.hari in va¯kyapad¯ıyam states (3.7.81-82),

pradha¯netayoryatra dravyasya kriyayoh. pr.thak ´saktirgun.¯as.raya¯ tatra pradha¯namanurudhyate 3.7.81

pradha¯navis.aya¯ ´saktih. pratyayena¯bhidh¯ıyate yad¯a gun.e tad¯a tadvad anukta¯pi praka¯´sate. 3.7.82

i.e., in case X is an argument of both the main verb as well as the subordinate verb, it is the main verb which assigns the case and the relation of X to the sub-ordinate verb gets manifested even without any other marking.

From the sentences

(16)  _r¯amah. dugdham˙ p¯ıtv¯a ´sa¯l¯am gacchati._

(17)  _r¯amen. a dugdham˙ p¯ıtv¯a ´sa¯l¯a gamyate._

it is clear that the vibhakti of _r¯ama_ is governed by the main verb _gam_. And hence, the information that _r¯ama_ is also the _karta¯_ of the verb _p¯a_ is not expressed through any of the suffixes. The ktv¯a suffix expresses only the precedence relation (pu¯rvaka¯l¯ınatva).

Similarly the su¯tra sama¯nakartr.kes.u (icch¯arthes.u) tumun (3.3.158) states that in case of verbs expressing desire, the infinitive verb in the subordinate clause will have the same kart¯a as that of the verb it modifies. Here also the primary information available from the non-finite verbal suffix _tumun_ is the relation of purpose.[[8]](#_ftn8)

The sharing in case of _ktva¯_ and _tumun_ suffixes is the result of the pre-conditions _sam¯anakartr.kayoh._ or _sam¯anakartr.kes.u_ in 3.4.21 and 3.3.158 respectively which act as Language Conventions.

# 3         Factors useful for S¯abdabodha´

As mentioned above, the generation problem is a direct problem, and the analysis problem is a reverse problem, and is non-deterministic. This problem was well recognised by the m¯ıma¯m˙ sakas who proposed four conditions viz. ¯aka¯n˙ks.¯a (expectancy), yogyata¯ (mutual compatibility), sannidhi (proximity) and ta¯tparya (intention of the speaker) as necessary conditions for proper verbal cognition. With the help of examples, we explain below, how the first three factors play an important role in the rejection of non-solutions from among the several possibilities. We have not discussed the importance of the fourth factor, since the kind of analysis it involves is out of the scope of the present discussion.

**3.1**      Ak¯an˙ks¯ .¯a **(Expectancy)**

In the sentence,

(18) _r¯amah. vanam˙ gacchati._

each of the 3 words in this sentence has multiple morphological analyses. ra¯mah. = ra¯ma {gender=m, case=1, number=sg},

= ra¯10 {lak¯ara=lat., person=1, number=pl, voice=active, parasmaipad¯ı}.

vanam˙ = vana {gender=n, case=1, number=sg},

= vana {gender=n ,case=2, number=sg}.

gacchati                  =               gam         {lak¯ara=lat.,        person=3,                  number=sg,          voice=active, parasmaipad¯ı},

= gacchat (gam ´satr.) {gender=m, case=1, number=sg}, = gacchat (gam ´satr.) {gender=n, case=1, number=sg}.

This may lead to the following two possible sentential analysis:

–    _r¯ama_ = kart¯a of the action indicated by _gam_, _vana_ = karma of the action indicated by _gam_.

–    _vana_ = karma of the action indicated by _r¯a_, _gacchati_ = simultaneity of the actions indicated by _r¯a_ and _gam_,

_vayam_ = kart¯a of the action indicated by the verb _r¯a_ (not expressed explicitly, but through the verbal suffix).[[9]](#_ftn9)

Of these two analysis, the second analysis can be ruled out on the basis of non-fulfilment of kart¯a and karma expectancies of the verb _gam_, and the samprada¯nam expectancy of the verb _r¯a_. The first analysis being complete in itself, it is preferred over the second one.

**3.2**          Yogyat¯a **(Compatibility)**

Consider the sentence,

(19) _´sakat.am˙ vanam˙ gacchati._

The possible morphological analyses of each of the three words are given below.

´sakat.am = ´sakat.a {gender=n, case=1, number=sg},

= ´sakat.a {gender=n, case=2, number=sg}.

vanam˙ = vana {gender=n, case=1, number=sg},

= vana {gender=n, case=2, number=sg}.

gacchati                  =               gam         {person=3,            lak¯ara=lat.,                  number=eka,       voice=active, parasmaipad¯ı},

= gacchat (gam+´satr.) {gender=m, case=1, number=sg}, = gacchat (gam+´satr.) {gender=n, case=1, number=sg}.

Now, more than one word can’t have the same ka¯raka role unless it is already expressed (abhihita). This leads to the following possible sentential analyses[[10]](#_ftn10):

–    _´sakat.a_ = kart¯a of the action indicated by _gam_, _vana_ = karma of the action indicated by _gam_.

–    _vana_ = kart¯a of the action indicated by _gam_, _´sakat.a_ = karma of action indicated by _gam_.

–    _vana_ = kart¯a of the action indicated by _gam_, _´sakat.a_ = modifier of _vana_.

–    _vana_ = karma of the action indicated by _gam_, _´sakat.a_ = modifier of _vana_.

Out of these, the last two do not fulfill all the mandatory expectancies of a verb. Among the first two, the first one is preferable over the second one, since _´sakat.a_ has an ability to move while _vana_ can not move. Hence _´sakat.a_ is preferable as a kart¯a of the verb _gam_ than _vana_. Thus the yogyata¯ or the competency of the nouns to be eligible candidates for the ka¯raka roles plays an important role here. However, the context may overrule the condition of yogyata¯. It is possible to have a reading where, all the residents of vana are going to see the new ´sakat.a, and thus _vana_ qualifies to be a kart¯a. The yogyata¯ and the context thus compete with each other and hence one needs discourse analysis to prune some of the possibilities.

**3.3**           Sannidhi **(Proximity)**

Consider,

(20) _r¯amah. dugdham p¯ıtv¯a ´sa¯l¯am gacchati._ Here the possible analyses are:

–    _r¯ama_ = kart¯a of _gam_, _dugdha_ = karma of _p¯a_, _´sa¯l¯am_ = karma of _gam_, _p¯a_ = preceding action with respect to _gam_.

–    _r¯ama_ = kart¯a of _gam_, _dugdha_ = karma of _gam_,

_´sa¯l¯am_ = karma of _p¯a_, _p¯a_ = preceding action with respect to _gam_.

A competent speaker rules out the second solution on account of non-compatibility of the arguments viz. _dugdha_ and _´sa¯l¯a_ do not have semantic competence to be the karma of _gam_ and _p¯a_ respectively.

The arguments in the correct solution are closer. We mark the words by their positions, and define the proximity measure of a relation as the distance between its two arguments, and the proximity measure of a solution as the sum of the proximity measures of the various relations in the parse. The proximity measure of the above two parses is

–    _r¯ama_ = kart¯a of _gam_

(dist = position of _gam_ - position of _r¯ama_ = 5 -1 = 4) _dugdha_ = karma of _p¯a_ (dist = 3-2 = 1) _´sa¯l¯am_ = karma of _gam_ (dist = 5-4 = 1)

_p¯a_ = preceding action with respect to _gam_ (dist = 5-3 = 2)

Thus the total distance = 4 + 1 + 1 + 2 = 8

–    _r¯ama_ = kart¯a of _gam_ (dist = 5-1 = 4) _dugdha_ = karma of _gam_ (dist = 5-2 = 3) _´sa¯l¯am_ = karma of _p¯a_ (dist = 4-3 = 1)

_p¯a_ = preceding action with respect to _gam_ (dist = 5-3 = 2) Thus the total distance = 4 + 3 + 1 + 2 = 10

The one with greater proximity (or smaller distance) is preferred as a solution. Though Sanskrit is a free-word-order language, the following sentence with exchange of the karmas is not acceptable.

(21)  *_r¯amah. ´sa¯l¯am p¯ıtv¯a dugdham˙ gacchati._

Equally unacceptable prose orders are

(22)  *_r¯amah. p¯ıtv¯a ´sa¯l¯am dugdham˙ gacchati._ (23) *_r¯amah. dugdham ´sa¯l¯am p¯ıtv¯a gacchati._

which involve crossing of links expressing the relations. A small pilot study of anvaya of Sam˙ ks.epa R¯am¯ayan.a (Kutumbashastri, 2002) sentences show no evidence of crossing of links.

It is worth exploring the Calder mobile model suggested by Staal (1967) and further worked out by Gillon (1993) in the light of the m¯ıma¯m˙ sa¯ principle of sannidhi. It may result in a better computational criterion for sannidhi.

# 4         Design Principles

The foregoing discussions lead to the following design principles for the constraint-based parser.

1.    The relations will be marked as ka¯raka relations.

[Using these ka¯raka relations and extra-linguistic knowledge, the semantic analysis may be carried out in the next level of processing.]

2.    Only those relations that are marked directly by the morphemes will beextracted.

[No relations that require some post-processing, or are based on secondary information will be extracted in the first step. The next level of processing will use this information to mark the unspecified or shared relations, if any.]

3.    To prioritize the solutions, only the conditions of ¯aka¯n˙ks.¯a and sannidhi will be used.

[The condition of yogyata¯ will be used as and when the information is available in machine usable form, with the understanding that this knowledge may not be relied on completely.]

4.    While dealing with prose, it will be assumed that there is no cross-linking ofthe relations between the words.

# 5         Mathematical Model

Let each word in a sentence be represented as a node in a graph, and the nodes be connected by the directed labelled edges. Then the problem of parsing a sentence may be modelled as

Given a Graph G with _n_ nodes, the task is to find a sub-graph T which is a directed Tree.[[11]](#_ftn11)

Assuming that the words can be partitioned into two classes viz. the words which have an expectancy called demand words and the words which satisfy the demand called source words, Bharati et. al. reduced the parsing problem to matching a bipartite graph (Bharati,1995; 96). But in reality, the words can not be partitioned into two classes. We come across words which can be demand words in some context and source words in some other context, or in the same context a kr.danta (primary derivative), e.g. can be both a demand word as well as a source word. Bharati et. al. (1995; 91) also needed the requirement of ka¯rakas and their optionality for each verb. But then, a parser based on such information will fail to parse sentences with ellipsis, or the real corpus where we come across sentences with incomplete information.

With a robust parser, that produces at least partial solution in case of ellipsis, as an aim, we relax the above conditions. So we give away the constraint that a word can be exclusively either a demand or a source word. Further we treat all ka¯rakas at the same level, irrespective of whether they are mandatory or optional, and assign penalty to lower the priority of those solutions which do not satisfy the mandatory expectancies.

We divide the problem into three parts:

1.    For a given sentence, draw all possible labeled directed edges among thenodes.

2.    Identify a sub-graph _T_ of _G_ such that _T_ is a directed Tree which satisfies the given constriants.

3.    Prioritize the solutions, in case there is more than one possible directed Tree.In what follows we describe our model.

A matrix is a convenient way of representing the graphs for computing purpose. In our case, each word represents a node of a graph, and with each pair of nodes is associated zero or more labels, indicating the possible relations between these nodes. The strong constraint on these relations is that there can be at the most one label associated with a pair of nodes. This then naturally suggests a 3D matrix representation, whose elements are either 0 or 1, where the 3 dimensions represent two nodes and a relation label. Further, each word has one or more morphological analyses. Hence, corresponding to each node there exists a record with one or more cells, each cell representing one morphological analysis of the word. Let the _jth_ analysis of the _ith_ node be represented by [_i,j_]. Thus the address of a typical element of the 3D matrix is ([_i,j_]_,R,_[_l,m_]). The first pair of letters _i_ and _j_ correspond to the source word analysis, while the second pair of letters _l_ and _m_ represent the demand word analysis. _R_ is the name of the relation of the _lth_ word to the _ith_ word. _j_ indicates the morphological analysis of the _ith_ word responsible for this relation, and _m_ indicates the morphological analysis of the _lth_ word that triggers this relation. In short the tuple ([_i,j_]_,R,_[_l,m_]) represents a relation _R_ due to the _mth_ morphological analysis of the _lth_ word to _ith_ word due to its _jth_ morphological analysis. For ease of representation, we represent the tuple as (_i,j,R,l,m_). Thus, the initial graph with all possible relations between various nodes is represented as 5D matrix _C_ such that _C_[_i,j,R,l,m_] = 1, if such a relation exists, = 0, otherwise.

**Task 1:** Based on the available information in a given sentence in the form of abhihitatva, vibhakti, sa¯m¯an¯adhikaran.ya, and the expectancies the matrix _C_ is populated with 0s and 1s.

Here are sample rules (just enough to illustrate an example), expressed in

English.

Rule 1:

If the sentence has a noun(say ‘s’) in pratham¯a vibhkati,

a verb(say ‘t’) in kartari prayogah., in 3rd person, and

‘s’ and ‘t’ agree in number, then ‘s’ is possibly a kart¯a of ‘t’.

Rule 2:

If the sentence has a noun(say ‘s’) in dvit¯ıy¯a vibhkati,

a verb(say ‘t’) in kartari prayogah., and is sakarmaka (roughly transitive)

then ‘s’ is possibly a karma of ‘t’.

Rule 3:

If the sentence has a noun(say ‘s’) in saptam¯ı vibhkati, and a verb(say ‘t’),

then ‘s’ is possibly an adhikaran.a of ‘t’.

Now consider the sentence

(24) _r¯amah. vanam˙ gacchati_.

The analyses of various words are numbered as follows:

[1_,_1]: ra¯ma {gender=m, case=1, number=sg},

[1_,_2]: ra¯ {gan.ah.=_ada¯di_, lak¯ara=lat., person=1, number=pl, prayogah.=kartari, parasmaipad¯ı}.

[2_,_1]: vana {gender=n, case=1, number=sg}, [2_,_2]: vana {gender=n ,case=2, number=sg}.

[3_,_1]: gam {lak¯ara=lat., person=3, number=sg, voice=active, parasmaipad¯ı},

[3_,_2]: gacchat (gam ´satr.) {gender=m, case=1, number=sg}, [3_,_3]: gacchat (gam ´satr.) {gender=n, case=1, number=sg}.

The above 3 rules with this input then produce the following output showing all possible relations between various analses:

[2_,_2] is a possible karma of [3_,_2] [2_,_2] is a possible karma of [3_,_3] [2_,_2] is a possible karma of [1_,_2]

[2_,_2] is a possible karma of [3_,_1]

[2_,_1] is a possible kart¯a of [3_,_1]

[1_,_1] is a possible kart¯a of [3_,_1]

The resulting graph is shown in Figure 2.

![](file:///C:/Users/ivan.MODULEMAX/AppData/Local/Packages/oice_16_974fa576_32c1d314_3514/AC/Temp/msohtmlclip1/01/clip_image005.jpg)

**Fig.2.** Graph showing all possible relations

**Task 2:** In order to get a Tree from this graph, we impose the following constraints.

1.    A morpheme(vibhakti) marks only one relation.

I.e., a node can have one and only one incoming arrow.

P_j,R,k,l C_[_i,j,R,k,l_] = 1, ∀_i._

2.    Each ka¯raka relation is marked by a single morpheme.

There can not be more than one outgoing arrow with the same label from the same cell, if the relation marks a ka¯raka relation,[[12]](#_ftn12) i.e. there can not be two words satisfying the same ka¯raka role of the same verb. P_i,j C_[_i,j,R,k,l_] = 1, for each tuple (_R,k,l_).

3.    A morpheme does not mark a relation to itself.

A word can’t satisfy its own expectancy. i.e. a word can’t be linked to itself[[13]](#_ftn13). Or there can not be self loops in a graph. P_j,R,k C_[_i,j,R,i,k_] = 0, ∀_i_.

4.    Only one valid analysis of every word per solution

(a)    If a word has both an incoming arrow as well as an outgoing arrow,they should be through the same cell.

∀_i_∀_j_ P_R,l,n C_[_i,j,R,l,n_] + P_a,b,R,k_!=_j C_[_a,b,R,i,k_] ≤ 1.

(b)    If there is more than one outgoing arrow through a node, then it shouldbe through the same cell. if, for some i,j,R,l,m C[i,j,R,l,m] = 1, then ∀_a_∀_b_∀_R_P_a,b,R,k_!=_j C_[_a,b,R,l,k_] = 0_._

5.    All the words in a sentence should be connected.[[14]](#_ftn14)

6.    There are no crossing of links

If all the nodes are plotted in a straight line, then they should not intersect each other. i.e., if _C_[_i,j,R,k,l_] = 1, then

∀_v_∀_yC_[_u,v,w,x,y_] = 0_,_ if i _<_ x _<_ k and u _<_ i or u _>_ k.

The resultant graph is a Tree provided:

1.    It is connected[[15]](#_ftn15).

2.    It has n-1 edges.

The fact that only sup / tin˙ suffix in every word marks a relation with some other word in a sentence, and abhihita ka¯raka is not expressed by any sup suffix, it is guaranteed that there are exactly n-1 edges.

**Task 3:** The solutions are prioritized using the conditions specified below.

For each of the solutions, the cost is calculated as

Cost = P_i,R,j c__iRj_, where

i)     _ciRj_ = |_j_ − _i_| ∗ _wtR_, if _C_[_i,a,R,j,b_] = 1 for some _a_ and _b_. = 0 otherwise.

ii)   _wtR_ = _rank_(_R_), if R is a ka¯raka relation (appendix I shows the ranking) = 100, otherwise.

This cost ensures the following:

1.    ¯aka¯n˙ks.¯a (k¯araka relation) is preferred over other relations (rank[[16]](#_ftn16) of the relations takes care of this.).

2.    The ranking of the solutions on the basis of distance-based weights takescare of sannidhih..

# 6         Implementation

The first task demands the inputs from grammar, whereas the second and the third tasks are purely mathematical ones, which can be handled by a constraint solver. The separation of tasks into three sub-tasks makes it not only modular, but also easy for a grammarian to test his/her rules independently. For the first task, an expert shell CLIPS is being used, whereas for the second task, a constraint solver MINION is being used. The system is available at http://sanskrit.uohyd.ernet.in/~anusaaraka/sanskrit/MT/test_skt.html

There is no specific reason behind using these special software tools except the familiarity and the availability under the General Public License. No special efforts were put in towards the efficiency of the system since the main purpose of this exercise is to have a proof of the concept.

# 7         Performance

The current system allows only _padaccheda-sahita-eka-tin˙-gadya-v¯akyam_. To measure the performance of this parser, we used hand tagged data. Around 110 sentences with single finite verb were selected from a school book (see appendix A for a sample). These sentences were tagged manually showing the relation of each word in the context. The sentences being simple, each sentence had a single possible parse in the context. There were 525 token words. The average length of the sentences was approximately 5, with a maximum length of 14 words. Morphological analyser is a pre-requisite for a parser. In order to avoid the cascading effect of errors due to non-availability of the morphological analysis, before running the parser, we ensured that the correct morphological analysis of all the words is being produced. Thus, given all possible correct analyses of the words, the task of the parser was to come up with a correct parse. Though the parser produces multiple parses, for the evaluation purpose, we chose only the first parse. Among the 113 sentences, 97 (86%) sentences had the first parse correct and 16 (14%) sentences had one relation wrong. Out of these 16, 10 relations had wrong label, 3 had wrong attachments and 3 went wrong in both the label as well as attachments.

The analysis of wrong results showed that most of the wrong relations were due to non-availability of appropriate knowledge to make the fine-grained distinction. For example, manually tagged corpus makes a distinction between ka¯la-adhikaran.a and de´sa-adhikaran.a, gaun.a and mukhya karma in case of dvi-karmaka (di-transitive) verbs, hetu and karan.am, to name a few. Another cause of ambiguity was the verbs in the cur¯adi (10th) gan.a. For most of the verbs in this class, the causative and non-causative forms are the same. This then leads to a wrong parse, since we also allow elipsis. In case there are n (_>_ 1) adjectives, there can be more than one possible way these adjectives can group with the following noun. But we produce a single parse where the adjectives are linked as a chain with the rightmost adjective qualifying the noun directly. This chain just indicates a chunk, and the internal grouping of these adjectives and also their relation with the head noun is left to the user for interpretation. A sample output of a sentence

_ba¯lyaka¯le r¯amah. da´sarathasya ¯ajn˜ay¯a vi´sva¯mitrasya yajn˜am r¯aks.asebhyah. raks.itum vanam agacchat._ is produced in Figure 3.

![](file:///C:/Users/ivan.MODULEMAX/AppData/Local/Packages/oice_16_974fa576_32c1d314_3514/AC/Temp/msohtmlclip1/01/clip_image007.jpg)

**Fig.3.** Sample parse output

# 8         Challenges

The result with limited test cases is encouraging. The real corpus, even with small children’s stories involves much more complex constructions, not necessarily confining to ‘eka tin˙ va¯kyam’. The constructions involve co-ordination between two or more verbs, sentence connectives such as ‘yad¯a-tada¯, yath¯a-tath¯a, atha, tasm¯at’, etc. Thus, even at the level of simple texts, one can not do away with discourse analysis.

Another important problem that needs to be addressed is to handle a little more semantics than can be handled with syntactico-semantic relations. For example, it would be desirable to distinguish between hetu and karan.a at least, though not between mukhya karma and gaun.a karma.

Third problem is regarding the upapadas. Upapada acts more like a function word (dyotaka) than a content word (v¯acaka). So in case of upapadas, it would be desirable to group the upapada together with the content word in the vibhakti it demands and then mark its relation with other content word. Thus e.g. in the sentence _r¯amah. munina¯ saha vanam˙ agacchat_, it is desirable to parse it as in figure 4 than as in figure 5. This means a upapada should be treated as a function word, and as such should not be represented by a node.

![](file:///C:/Users/ivan.MODULEMAX/AppData/Local/Packages/oice_16_974fa576_32c1d314_3514/AC/Temp/msohtmlclip1/01/clip_image010.gif)

**Fig.5.** saha-content

The vibhaktis, as we know, denote more than one meaning. For example, the second case suffix denotes the meaning of _kriya¯vi´ses.an. a_ (manner), _ka¯la_ (time) or _adhvan_ (path) in addition to the _karma_. To decide an appropriate role, now what one requires is the knowledge of yogyata¯. In other words, our e-dictionaries should be rich with semantic properties of the words such as whether it denotes time, path or the manner, etc.

Since the parser does the analysis ‘mechanically’, it detects the problems of ‘violation’ of the rules more easily. We give just one example (more examples can be found in Gillon, 2002) from the anvaya of ‘Sam˙ ks.epa R¯am¯ayan.am’.

guhena laks.man.ena s¯ıtaya¯ ca sahitah. ra¯mah. vanena vanam˙ gatv¯a bahu¯dak¯ah. nad¯ıh. t¯ırtva¯ bharadv¯ajasya ´sa¯sana¯t citraku¯t.am anupr¯apya vane ramyam ¯avasatham˙ kr.tv¯a devagandharvasan´k¯a´sa¯h. te trayah. ramama¯n.¯ah. sukham˙ nyavasan. (Sloka 30-32)´

This sentence poses the following problems:

a)   Whom does the phrase ‘te trayah.’ refer to?

b)   _r¯amah._ does not agree with the finite verb _nyavasan_. Is it not a violation of _sam¯anakartr.kayoh. pu¯rvak¯ale_?

c)    Does _gatva¯_ precede _t¯ırtva¯_ or _nyavasan_?

d)   In case of _vanena vanam˙_ what should be the meaning of the third case?

In spite of these problems, this parser can act as a tool to discover various kinds of semantic knowledge necessary to build a semantic parser.

# 9         Acknowledgement

This work is a part of the Sanskrit Consortium project entitled ‘Development of Sanskrit computational tools and Sanskrit-Hindi Machine Translation system’ sponsored by the Government of India.

# References

1.       Bharati, Akshar and Sangal, Rajeev, _A Karaka Based Approach to Parsing of Indian Languages_, In _COLING90: Proc. of Int. Conf. on Computational Linguistics (Vo l. 3), Helsinki_, Association for Computational Linguistics, NY, August 1990.

2.       Bharati, Akshar, Chaitanya, Vineet and Sangal, Rajeev, _NLP A Paninian Perspective_, Prentice Hall of India, Delhi, 1994.

3.       Cardona George, _P¯an. ini and P¯an. in¯ıyas on ´ses.a Relations,_ Kunjunni Raja Academy of Indological Research, Kochi, 2007.

4.       Dash Achyutanand, _The syntactic role of adhi in the P¯aninian Ka¯raka system_ in P¯an.inian Studies Prof. S. D. Joshi Felicitation volume, ed. Deshpande Madhav M, and Bhate Saroja, Center for South and Southeast Asian Studies, University of Michigan, U.S.A., 1991.

5.       Gent, Ian P., Jefferson, Chris and Miguel, Ian. _MINION: A Fast, Scalable, Constraint Solver,_ The European Conference on Artificial Intelligence 2006 (ECAI 06).

6.       Gillon Brendan S. _Word Order in Classical Sanskrit_ Indian Linguistics, v.57, n.1, pp. 1-35, 1996.

7.       Gillon Brendan S. _Bhartr.hari’s rule for unexpressed k¯arakas: The problem of control in Classical Sanskrit_ Indian Linguistic Studies, Festschrift in Honor of George Cardona, Ed. Deshpande, Hook, Motilal Banarasidass, Delhi, 2002.

8.       Hellwig, Oliver, _Extracting Dependency Trees from the Sanskrit Texts_ Proceedings of the Sanskrit Computational Linguistics Symposium, Ed. Kulkarni and Huet, LNAI 5406, Springer Verlag, 2009.

9.       Huet, G´erard, Formal Structure of Sanskrit Text: Requirements Analysis for a Mechanical Sanskrit Processor Proceedings of the Sanskrit Computational Linguistics Symposium, Ed. Huet, Kulkarni and Sharf, LNAI 5402, Springer Verlag, 2009.

10.    Huet, G´erard, Shallow syntax analysis in Sanskrit guided by semantic nets constraints Proceedings of International Workshop on Research Issues in Digital Libraries, Ed. Majumder, Mitra and Parui, ACM Digital Library, Dec 2006.

11.    Jigyasu, Brahmadatt, 1979. _Ashtadhyayi (Bhashya) Prathamavrtti, three volumes_, Ramlal Kapoor Trust Bahalgadh, (Sonepat, Haryana, In dia) (In Hindi)

12.    Joshi, S.D. (editor) 1968. _Patanjali’s Vyakarana Mahabhashya_, (several volumes), Univ. of Poona, Pune, India.

13.    Joshi, S.D. and Roodebergen J.A.F., 1998. _The A´st.¯adhy¯ay¯ıof P¯an. ini_ (several volumes), Sahitya Akademi, Delhi, India.

14.    Kiparsky, P. _On the Architecture of Panini’s Grammar_, Proceedings of the Sanskrit Computational Linguistics Symposium, Ed. Huet, Kulkarni and Scharf, LNAI 5402, Springer Verlag, 2009.

15.    Kutumbashastri, V. _Sam˙ ks.epa Rama¯yan. am_, Teach Yourself Samskrit series, ed., Rashtriya Sanskrit Samsthanam, New Delhi, 2002.

16.    Lin D. _Dependency-based evaluation of MINIPAR._ In Workshop on the evaluation of Parsing Systems, Granada, Spain, 1998.

17.    Marneffe M., MacCartney B. and Manning C. D. _Generating Typed Dependency Parses from Phrase Structure Parses_ The fifth international conference on Language Resources and Evaluation, L REC 2006, Italy.

18.    Pande, Gopal Dutt _Vaiya¯karan. a Siddha¯ntakaumud¯ı of Bhattojidikshita_ (Text only), Reprint Edition. Varanasi: Chowkhamba Vidyabhavan, 2000.

19.    Ramakrishnamacharyulu, K.V. _Annotating Sanskrit Texts based on S¯abdabodha´ systems,_ Proceedings of the Sanskrit Computational Linguistics Symposium, Ed. Kulkarni and Huet, LNAI 5406, Springer Verlag, 2009.

20.    Ramanujatatacharya, N.S. _S¯abdabodha´ M¯ım¯am˙ sa¯_ Institute Francis De Pondicherry, 2005.

21.    Sharma, Raghunath _Va¯kyapad¯ıyam, Part III_ With commentary Prak¯a´sa by Helaraja and Ambakartri Varanaseya Sanskrit Visvavidyalaya, Varanasi, 1974.

22.    SK: Siddha¯ntakaumud¯ı See Pande

23.    Staal, J.F. _Word Order in Sanskrit and Universal Grammar_ Reidal, Dordercht (Foundations of Language, Supplementary series: v.5), 1967.

24.    Sleator D. D., Temperley D. _Parsing English with a link grammar_ In third international Workshop on Parsing Technologies, 1993.

# A        Sample story

nady¯ah. tat.e ekah. vr.ks.ah. asti| vr.ks.asya sam¯ıpam eka¯ ´sila¯ asti| vr.ks.asya ´sa¯ka¯su n¯ıd¯ah˙ . santi| n¯ıd.es.u vihaga¯h. vasanti| n¯ıd.¯ah. vihaga¯n raks.anti| vr.ks.asya adhah. va¯nara¯h. santi| kapayah. gr.ham na racayanti| te sarvad¯a itastatah. bhramanti| ekasmin divase ´s¯ıtam ta¯n p¯ıd.ayati| te ´s¯ıta¯t tr¯an.¯aya agnim icchanti| kutr¯api te agnim na vindanti| ekah. gun˜ja¯ya¯h. phal¯ani pa´syati| gun˜ja¯ya¯h. phal¯ani rakta¯ni santi| sah. agneh. sadr.´sa¯ni gun˜ja¯ya¯h. phal¯ani ¯anayati| ta¯ni gun˜ja¯ya¯h. phal¯ani ´sila¯ya¯m sam˙ harati| te sarve gun˜ja¯-phalam paritah. upavi´santi| agneh. icchaya¯ te mukhaih. ta¯ni dhamanti| te agnim na vindanti| te va¯nara¯h. anala¯ya vr.th¯a ¯aya¯sam kurvanti| tes.¯am ´s¯ıtam na na´syati| kapayah. mu¯rka¯h. santi|

# B       Relations

The relations used, along with their ranks are given in Table 1.

|   |   |   |   |
|---|---|---|---|
|(0)|upapada vibhakti|(12)|k¯ala-adhikaran.am˙|
|(1)|karta¯|(13)|vis.aya-adhikaran.am˙|
|(2)|prayojaka karta¯|(14)|karta¯-sam¯ana¯dhikaran.am˙|
|(3)|prayojya karta¯|(15)|vi´ses.an.am˙|
|(4)|karma|(16)|kriy¯a-vi´ses˙an.am˙|
|(5)|reserverd for gaun.akarma|(17)|t¯adarthya|
|(6)|reserverd for mukhyakarma|(18)|pu¯rvaka¯l¯ına|
|(7)|karan.am˙|(19)|sambandha|
|(8)|samprad¯anam˙|(20)|k¯araka s.as.t.h¯ı|
|(9)|apa¯da¯nam˙|(21)|nis.edha|
|(10)|adhikaran.am˙|(22)|sambodhana|
|(11)|de´sa-adhikaran.am˙|||

**Table 1.** Relations

  

---

[[1]](#_ftnref1) Thanks to G´erard Huet and Peter Scharf for their valuable remarks.

[[2]](#_ftnref2) roughly                _ekatin˙    v¯akyam  (v¯arttika                 on             tva¯mau  dvit¯ıya¯y¯ah.            8.1.23, halantapum˙ llin˙gaprakaran. am)._

[[3]](#_ftnref3) the word ‘case’ is used for _vibhakti_.

[[4]](#_ftnref4) There are two more possibilities, since both have the same gender, number, and vibhakti, one can be an adjective of the other.

[[5]](#_ftnref5) The issues in the development of a statistical parser are totally different. They are related to the size of the annotated corpus, the number of annotated tags used, their fine-grained-ness, etc.

[[6]](#_ftnref6) tin˙kr.ttaddhitasama¯saih. parisam˙ khy¯anam (ma. bh¯a. 2.3.1. v¯a.)

[[7]](#_ftnref7) kartr.karman.oh. kr.ti (2.3.65)

[[8]](#_ftnref8) tumunn.vulau kriy¯aya¯m kriy¯arthy¯aya¯m (3.3.10) 10 _ra¯_ in the sense of _d¯ane_ from the second (_ad¯adi_) gan.ah.

[[9]](#_ftnref9) The sentence is interpreted as - (tasmin) gacchati (sati), vayam˙ vanam˙ r¯amah.

As (he) goes, let us give the forest (to somebody).

[[10]](#_ftnref10) Assuming that the modifier is to the left, which need not be true in case of poetry.

[[11]](#_ftnref11) A tree is a graph in which any two vertices are connected by exactly one simple path.

[[12]](#_ftnref12) adhikaran.am is treated as an exception since one can have more than one adhikaran.am as in ra¯mah. adya pan˜ca v¯adane gr.ham agacchat.

[[13]](#_ftnref13) in case of some of the taddhita suffixes which are in sv¯artha, there will be self loops. But we do not consider the meaning of taddhita suffixes in the first step, and thus can avoid the self loops

[[14]](#_ftnref14) This condition is not yet implemented.

[[15]](#_ftnref15) Since, this condition is not yet implemented, the resulting graph need not be a Tree.

[[16]](#_ftnref16) Better ranking scheme needs to be developed to take care of default word order.
Feature: BG 2.47 - Heritage lemmatization through L0 MCP service

  Scenario: Fused karmanyevaadhikaraste yields lemma adhikAra
    Given raw file "l0_data/raw/bg/vedabase.io/chapter-02.md" contains BG TEXT 47
    When I analyze BG TEXT 47 via L0 MCP
    Then SPIR tokens contain lemma "अधिकार"
    And SPIR has heritage morphology details

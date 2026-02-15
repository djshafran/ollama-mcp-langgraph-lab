Feature: BG 2.47 - Syntax and KAG through L0 MCP service

  Scenario: BG 2.47 produces non-empty SPIR and KAG
    Given raw file "src/l0/data/raw/bg/vedabase.io/chapter-02.md" contains BG TEXT 47
    When I analyze BG TEXT 47 via L0 MCP
    Then SPIR tokens are present
    And SPIR has KAG graph

  Scenario: BG 2.47 builds karaka graph dependencies
    Given raw file "src/l0/data/raw/bg/vedabase.io/chapter-02.md" contains BG TEXT 47
    When I analyze BG TEXT 47 via L0 MCP
    Then SPIR capabilities include "paninian_syntax"
    And SPIR syntax paninian edges are present
    And SPIR paninian edges have roles
    And SPIR UD basic edges are present
    And SPIR UD includes relation "obl:loc"
    And SPIR has enhanced UD layer
    And SPIR has deontic norms

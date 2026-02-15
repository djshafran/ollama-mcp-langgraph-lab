Feature: L0 basic analysis

  Scenario: Normalize whitespace
    Given input text "  a   b \n c "
    When I analyze input text via L0 MCP
    Then SPIR normalized_text equals "a b c"
    And SPIR validates via L0 MCP

  Scenario: Simple analysis validates and builds v0.4 syntax and semantics
    Given input text "Om namah shivaya"
    When I analyze input text via L0 MCP
    Then SPIR validates via L0 MCP
    And SPIR syntax paninian edges are present
    And SPIR UD basic edges are present
    And SPIR has KAG graph

Feature: Simple Sanskrit sentence has karaka and UD mappings

  Scenario: Basic karaka and UD extraction
    Given input text "रामः वनं गच्छति"
    When I analyze input text via L0 MCP
    Then SPIR validates via L0 MCP
    And SPIR syntax paninian edges are present
    And SPIR paninian edges have roles
    And SPIR UD basic edges are present

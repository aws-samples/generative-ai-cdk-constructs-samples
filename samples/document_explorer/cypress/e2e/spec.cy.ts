describe('Make sure streamlit worked', () => {
  it('Visit website', () => {
    cy.visit('http://localhost:8501')
  })
})
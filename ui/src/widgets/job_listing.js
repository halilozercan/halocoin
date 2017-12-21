import React, { Component } from 'react';
import {axiosInstance} from '../tools.js';
import {
  Table,
  TableBody,
  TableHeader,
  TableHeaderColumn,
  TableRow,
  TableRowColumn,
} from 'material-ui/Table';
import {Card, CardActions, CardHeader, CardText} from 'material-ui/Card';
import RaisedButton from 'material-ui/RaisedButton';

class JobListing extends Component {

  constructor(props) {
    super(props);
    this.state = {
      data: null
    }
  }

  componentDidMount() {
    axiosInstance.get('/jobs').then((response) => {
      this.setState({data: response.data.available});
    });
  }

  bidFor = (job_id) => {
    alert('Bidding for ' + job_id);
  }

  render() {
    let content = 
    <TableRow>
      <TableHeaderColumn>Could not find available JOB</TableHeaderColumn>
    </TableRow>
    if(this.state.data !== null) {
      content = Object.keys(this.state.data).map((_row, i) => {
        console.log(this.state.data[_row]);
        return <TableRow>
          <TableHeaderColumn>{this.state.data[_row].id}</TableHeaderColumn>
          <TableHeaderColumn>10000</TableHeaderColumn>
          <TableHeaderColumn>{this.state.data[_row].status_list[0].block}</TableHeaderColumn>
          <TableHeaderColumn><RaisedButton label="Bid" primary={true} onClick={ () => {this.bidFor(this.state.data[_row].id)} } /></TableHeaderColumn>
        </TableRow>
      });
    }
    return (
      <Card style={{"margin":16}}>
        <CardHeader
          title="Available Jobs"
          subtitle="Bid on these jobs to get assigned"
        />
        <CardText>
          <Table selectable={false}>
            <TableHeader displaySelectAll={false} adjustForCheckbox={false}>
              <TableRow selectable={false}>
                <TableHeaderColumn>Job ID</TableHeaderColumn>
                <TableHeaderColumn>Max Reward</TableHeaderColumn>
                <TableHeaderColumn>Announced Block</TableHeaderColumn>
                <TableHeaderColumn>Auction</TableHeaderColumn>
              </TableRow>
            </TableHeader>
            <TableBody displayRowCheckbox={false}>
              {content}
            </TableBody>
          </Table>
        </CardText>
      </Card>
    );
  }
}

export default JobListing;